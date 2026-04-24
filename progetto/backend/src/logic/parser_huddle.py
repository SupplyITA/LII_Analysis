import os
import re
import html
import tempfile
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def get_domain(url: str) -> str:
    """ Restituisce il dominio in minuscolo da un URL dato """
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain

def clean_huddle_markdown(md_text: str) -> str:
    """
    Pulisce il markdown rimuovendo elementi social e pubblcitari
    tipici di Huddle
    """
    if not md_text: return ""

    md_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', md_text)
    
    lines = md_text.split('\n')
    clean_lines = []
    blacklist = ["pubblicità", "condividi", "facebook", "twitter", "adsbygoogle", "ph.credits"]
    
    for line in lines:
        l_str = line.strip()
        if l_str and not any(bad in l_str.lower() for bad in blacklist):
            if l_str.startswith('#') or len(l_str) > 30:
                clean_lines.append(l_str)
    return "\n\n".join(clean_lines)    

async def parser_huddle(url: str, html_raw: str = None) -> dict:
    """
    Esegue il parsing specifico per huddle.org.
    Acquisizione sia tramite URL sia tramite HTML locale (se presente)
    """    
    browser_cfg = BrowserConfig(
        headless=True,
        extra_args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
    )
    
    # configurazione del crawler    
    crawler_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        css_selector="article", 
        excluded_tags=['nav', 'aside', 'footer', 'script', 'style']
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
            result = await crawler.arun(url=target_url, config=crawler_cfg)
            
            if not result.success:
                raise Exception(f"Errore Huddle: {result.error_message}")
            
            # estrazione dinamica del titolo
            title = "Huddle Article"
            title_match = re.search(r'<title[^>]*>(.*?)</title>', result.html, re.IGNORECASE | re.S)
            if title_match:
                title = html.unescape(title_match.group(1)).split('|')[0].split('—')[0].strip()
            
            md_text = result.markdown
            

            if (title.lower() == "huddle" or "huddle" in title.lower()) and md_text:
                h1_match = re.search(r'^#\s+(.*)', md_text, re.MULTILINE)
                if h1_match: title = h1_match.group(1).strip()
            
            return {
                "url": url,
                "domain": get_domain(url),
                "title": title,
                "html_text": result.html,
                "parsed_text": clean_huddle_markdown(md_text)
            }
    finally:
        if temp_html_path and os.path.exists(temp_html_path):
            os.remove(temp_html_path)
