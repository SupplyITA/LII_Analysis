import os
import html
import re
import tempfile
import asyncio
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def get_domain(url: str) -> str:
    """ Restituisce il dominio in minuscolo da un URL dato """
    parsed = urlparse(url)
    return parsed.netloc.lower()

async def parser_grammy(url: str, html_raw: str = None) -> dict:
    """
    Esegue il parsing specifico per grammy.com.
    Acquisizione sia tramite URL sia tramite HTML locale (se presente)
    """       
    browser_cfg = BrowserConfig(headless=True, extra_args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
        
    # SCRIPT JS: Rimuove gli articoli successivi al primo e le sezioni di disturbo
    js_kill_infinite_scroll = """
    let articles = document.querySelectorAll('article');
    if (articles.length > 1) {
        for (let i = 1; i < articles.length; i++) {
            articles[i].remove();
        }
    }
    document.querySelectorAll('.read-more, .related-articles, .infinite-scroll').forEach(el => el.remove());
    """

    # configurazione del crawler
    crawler_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        css_selector="main", 
        excluded_tags=['header', 'footer', 'nav', 'aside', 'script', 'style', 'form'],
        js_code=js_kill_infinite_scroll
        # RIMOSSO: wait_for="domcontentloaded" che causava il blocco dei 60 secondi
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
                raise Exception(f"Errore durante il crawling: {result.error_message}")

            # estrazione dinamica del titolo
            title = result.metadata.get("title") if result.metadata else None        
            md_text = result.markdown or "" # evita che il titolo sia None
            
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
                    "domain": get_domain(url), 
                    "title": title,
                    "html_text": result.html, 
                    "parsed_text": md_text
                }
    finally:
        if temp_html_path and os.path.exists(temp_html_path):
            os.remove(temp_html_path)

# ==========================================
# TEST VISIVO VELOCE
# ==========================================
if __name__ == "__main__":
    async def test_veloce():
        test_url = "https://www.grammy.com/news/heavy-metal-music-latin-america-history/" 
        print(f"Test in corso su: {test_url}")
        res = await parser_grammy(test_url)
        print("\n--- TESTO PARSATO ---")
        print(res['parsed_text'])

    asyncio.run(test_veloce())