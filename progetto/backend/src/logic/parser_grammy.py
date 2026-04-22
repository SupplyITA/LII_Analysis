import asyncio
import os
import html
import re
import tempfile
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def get_domain(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.lower()

async def parser_grammy(url: str, html_raw: str = None) -> dict:
    browser_cfg = BrowserConfig(headless=True, extra_args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
    crawler_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        css_selector="main", 
        excluded_tags=['header', 'footer', 'nav', 'aside', 'script', 'style', 'form']
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
                raise Exception(f"Errore durante il crawling: {result.error_message}")

            title = result.metadata.get("title") if result.metadata else None        
            md_text = result.markdown or "" # <--- SALVAVITA: EVITA CHE SIA NONE
            
            if not title or title.lower() == "grammy":
                h_match = re.search(r'^#+\s+(.*)', md_text, re.MULTILINE)
                if h_match:
                    title = h_match.group(1).strip()

            if title:
                title = html.unescape(title)
                title = title.split('|')[0].split('—')[0].strip()
            else:
                title = "Grammy Resource"
            
            return {
                    "url": url, 
                    "domain": "grammy.com", 
                    "title": title,
                    "html_text": result.html, 
                    "parsed_text": md_text
                }
    finally:
        if temp_html_path and os.path.exists(temp_html_path):
            os.remove(temp_html_path)