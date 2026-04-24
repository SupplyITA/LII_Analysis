import os
import tempfile
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
import json
import re

def get_domain(url: str) -> str:
    """ Restituisce il dominio in minuscolo da un URL dato """
    parsed = urlparse(url)
    return parsed.netloc.lower()

async def parser_wikipedia(url: str, html_raw: str = None) -> dict:
    """
    Esegue il parsing specifico per wikipedia.
    Acquisizione sia tramite URL sia tramite HTML locale (se presente)
    """
    
    browser_cfg = BrowserConfig(headless=True, extra_args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
    
    # rimuove elementi non informativi 
    js_script = """
    document.querySelectorAll('sup, nav, footer, script, style, .infobox, .reflist, .navbox, .mw-editsection, .reference, .metadata, .printfooter').forEach(el => el.remove());
    let seeAlso = document.getElementById('See_also');
    if (seeAlso && seeAlso.parentNode) {
        while (seeAlso.parentNode.nextSibling) { seeAlso.parentNode.nextSibling.remove(); }
        seeAlso.parentNode.remove();
    }
    """
    # configurazione del crawler
    crawler_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, css_selector="#mw-content-text", js_code=js_script)

    # gestione del parsing di HTML diretto
    target_url = url
    temp_html_path = None
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
                raise Exception(f"Errore durante il crawling: {result.error_message}")

            # estrazione dinamica del titolo
            title = result.metadata.get('title', 'No Title Found') if result.metadata else "No Title Found"
            
            return {
                "url": url,
                "domain": get_domain(url),
                "title": title,
                "html_text": result.html,
                "parsed_text": result.markdown or ""
            }
    finally:
        if temp_html_path and os.path.exists(temp_html_path):
            os.remove(temp_html_path)
