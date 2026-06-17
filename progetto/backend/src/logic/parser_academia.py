import os
import re
import html
from urllib.parse import urlparse
import tempfile
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def get_domain(url: str) -> str:  
    """ Restituisce il dominio in minuscolo da un URL dato """     
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    return domain

def clean_academia_markdown(md_text: str) -> str:
    if not md_text: return ""

    md_text = re.sub(r'!\[.*?\]\(.*?\)', '', md_text)
    md_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', md_text)
    md_text = re.sub(r'(?i)(\bread more\b|\bcontinue reading\b|\.\.\.more)', '', md_text)

    lines = md_text.split('\n')
    clean_lines = []
    blacklist = [
        "download pdf", "related papers", "cookie policy", "privacy policy", 
        "log in", "sign up", "loading preview", "save to library", 
        "view full text", "skip to main content", "search academia", 
        "terms of use", "academia.edu"
    ]

    for line in lines:
        line_str = line.strip()
        if not line_str: continue
        if any(bad_word in line_str.lower() for bad_word in blacklist): continue
        if len(line_str) > 0 or line_str.startswith('#'):
            clean_lines.append(line_str)
    return "\n\n".join(clean_lines)

async def parser_academia(url: str, html_raw: str = None) -> dict:
    """
    Esegue il parsing specifico per academia.edu.
    Acquisizione sia tramite URL sia tramite HTML locale (se presente)
    """    
    browser_cfg = BrowserConfig(
        headless=True,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
        extra_args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-blink-features=AutomationControlled"]
    )
    
    # configurazione del crawler
    crawler_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        delay_before_return_html=5.0, 
        excluded_tags=['header', 'footer', 'nav', 'aside', 'script', 'style', 'form', 'img', 'svg']
    )

    target_url = url
    temp_html_path = None

    # gestione del parsing di HTML diretto
    if html_raw:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as f:
            f.write(html_raw)
            temp_html_path = f.name
        target_url = f"file://{temp_html_path}"

    try:
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            # processo di acquisizione
            result = await crawler.arun(url=target_url, config=crawler_cfg)
            if not result.success:
                raise Exception(f"Crawl fallito: {result.error_message}")

            # estrazione dinamica del titolo
            title = None
            og_match = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']', result.html, re.IGNORECASE)
            if not og_match:
                og_match = re.search(r'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']og:title["\']', result.html, re.IGNORECASE)
                
            title_match = re.search(r'<title[^>]*>(.*?)</title>', result.html, re.IGNORECASE | re.DOTALL)
            h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', result.html, re.IGNORECASE | re.DOTALL)

            if og_match: title = og_match.group(1)
            elif title_match: title = title_match.group(1)
            elif h1_match: title = h1_match.group(1)
                
            if not title or title.strip() == "" or title == "Academia Paper":
                try:
                    clean_url = url.split('?')[0].split('#')[0]
                    last_part = clean_url.rstrip('/').split('/')[-1]
                    title = last_part.replace('_', ' ').replace('-', ' ').strip()
                except:
                    title = "Academia Paper"

            title = html.unescape(title).replace(" | Academia.edu", "").strip()
            title = re.sub(r'^\s*\((?:PDF|DOC|DOCX)\)\s*', '', title, flags=re.IGNORECASE).strip()
            title = re.sub(r'<[^>]+>', '', title).strip()
            if not title: title = "Academia Paper"

            
            parsed_text = ""

            abs_match = re.search(r'class="[^"]*(?:abstract|summary|description|full-text)[^"]*">(.*?)</div', result.html, re.IGNORECASE | re.DOTALL)
            if abs_match:
                raw_abs = abs_match.group(1)
                
                
                clean_html = re.sub(r'<(style|script)[^>]*>.*?</\1>', ' ', raw_abs, flags=re.IGNORECASE | re.DOTALL)
                
                parsed_text = re.sub(r'<[^>]+>', ' ', clean_html)
                parsed_text = html.unescape(parsed_text)
                
                parsed_text = re.sub(r'^Abstract\s*', '', parsed_text, flags=re.IGNORECASE)
                parsed_text = re.sub(r'(?i)(\.?\.\.?\s*read more\b|\bcontinue reading\b|\.\.\.more)', '', parsed_text).strip()

            if len(parsed_text) < 50 and result.markdown:
                md_text = result.markdown
                if title and title != "Academia Paper":
                    parti = md_text.split(title)
                    if len(parti) > 1: md_text = parti[-1]
                
                spartiacque = ["Related Papers", "Download PDF", "Save to Library", "Citations", "Log In", "Cookie Policy", "Continue Reading"]
                for parola in spartiacque:
                    md_text = re.split(f'(?i){parola}', md_text)[0]
                parsed_text = clean_academia_markdown(md_text) 

            if len(parsed_text) < 50:
                desc_match = re.search(r'<meta[^>]+(?:name|property)=["\'](?:og:description|twitter:description|description)["\'][^>]+content=["\'](.*?)["\']', result.html, re.IGNORECASE | re.DOTALL)
                if not desc_match:
                    desc_match = re.search(r'<meta[^>]+content=["\'](.*?)["\'][^>]+(?:name|property)=["\'](?:og:description|twitter:description|description)["\']', result.html, re.IGNORECASE | re.DOTALL)
                if desc_match:
                    parsed_text = html.unescape(desc_match.group(1)).strip()
                if "Academia.edu is a platform for academics" in parsed_text:
                    parsed_text = ""

            parsed_text = re.sub(r'\s+', ' ', parsed_text).strip()

            return {
                "url": url, 
                "domain": get_domain(url), 
                "title": title,
                "html_text": result.html,
                "parsed_text": parsed_text
            }
    finally:
        if temp_html_path and os.path.exists(temp_html_path):
            os.remove(temp_html_path)
