import os
import re
import html
import tempfile
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def get_domain(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    return domain

def clean_huddle_markdown(md_text: str) -> str:
    if not md_text: return ""
    # rimuove i link mantenendo il testo
    md_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', md_text)
    lines = md_text.split('\n')
    clean_lines = []
    blacklist = ["pubblicità", "condividi", "facebook", "twitter", "adsbygoogle", "ph.credits"]
    for line in lines:
        l_str = line.strip()
        if l_str and not any(bad in l_str.lower() for bad in blacklist):
            # per mantenere solo titoli o paragrafi significativi
            if l_str.startswith('#') or len(l_str) > 30:
                clean_lines.append(l_str)
    return "\n\n".join(clean_lines)

async def parser_huddle(url: str, html_raw: str = None) -> dict:
    browser_cfg = BrowserConfig(
        headless=True,
        extra_args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
    )
    
    crawler_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        css_selector="article", 
        excluded_tags=['nav', 'aside', 'footer', 'script', 'style'],
        excluded_selector=".share-buttons, .stream-item, .post-meta" 
    )
    
    target_url = url
    temp_html_path = None
    if html_raw:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as f:
            f.write(html_raw)
            temp_html_path = f.name
        target_url = f"file://{temp_html_path}"

    try:
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=target_url, config=crawler_cfg)
            if not result.success:
                raise Exception(f"Crawl fallito: {result.error_message}")
            
            # estrazione dinamica del titolo
            extracted_title = ""
            
            json_ld_match = re.search(r'"headline"\s*:\s*"(.*?)"', result.html)
            if json_ld_match:
                extracted_title = json_ld_match.group(1)
            
            if not extracted_title:
                og_match = re.search(r'property=["\']og:title["\']\s+content=["\'](.*?)["\']', result.html, re.I)
                if not og_match:
                    og_match = re.search(r'content=["\'](.*?)["\']\s+property=["\']og:title["\']', result.html, re.I)
                if og_match:
                    extracted_title = og_match.group(1)

            if not extracted_title:
                t_tag = re.search(r'<title[^>]*>(.*?)</title>', result.html, re.I | re.S)
                if t_tag:
                    extracted_title = t_tag.group(1)

            # fallback finale 
            if not extracted_title:
                extracted_title = "Huddle Article"

            # pulizia e formattazione finale del titolo
            final_title = html.unescape(extracted_title)
            final_title = final_title.split('|')[0].split('—')[0].split(' – ')[0].strip()
            
            # gestione md_text per evitare errori di definizione
            current_md = result.markdown if result.markdown else ""

            return {
                "url": url,
                "domain": get_domain(url),
                "title": final_title,
                "html_text": result.html,
                "parsed_text": clean_huddle_markdown(current_md)
            }
    finally:
        if temp_html_path and os.path.exists(temp_html_path):
            try: os.remove(temp_html_path)
            except: pass

