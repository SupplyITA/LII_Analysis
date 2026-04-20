import asyncio
import json
import os
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def get_domain(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.lower()

async def parser_grammy(url: str, html_raw: str = None) -> dict:
    """Parser per Grammy.com usando solo Crawl4AI."""
    browser_cfg = BrowserConfig(headless=True)
    
    crawler_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        css_selector="main", 
        excluded_tags=['header', 'footer', 'nav', 'aside', 'script', 'style', 'form']
    )
    
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        target = f"raw:{html_raw}" if html_raw else url
        result = await crawler.arun(url=target, config=crawler_cfg)
        
        if not result.success:
            raise Exception(f"Errore durante il crawling: {result.error_message}")
        
        title = result.metadata.get('title', 'Grammy News') if result.metadata else "Grammy News"
        
        return {
            "url": url, 
            "domain": get_domain(url), 
            "title": title,
            "html_text": result.html, 
            "parsed_text": result.markdown
        }
    
if __name__ == "__main__":
    test_url = "INSERISCI_QUI_URL_GRAMMY" 
   
    mio_gold_text_manuale = """ 
    
    """
   
    filename = "grammy.com_gs.json"
   
    try:
        print(f"Scaricamento di {test_url} in corso...")
        res = asyncio.run(parser_grammy(test_url))
        
        nuova_entry = {
            "url": res['url'],
            "domain": res['domain'],
            "title": res['title'],
            "html_text": res['html_text'], 
            "gold_text": mio_gold_text_manuale.strip()
        }

        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                try:
                    dati_esistenti = json.load(f)
                except json.JSONDecodeError:
                    dati_esistenti = []
        else:
            dati_esistenti = []

        dati_esistenti.append(nuova_entry)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(dati_esistenti, f, indent=4, ensure_ascii=False)
            
        print("-" * 30)
        print(f"SUCCESSO: Pagina '{res['title']}' aggiunta.")
        print(f"Pagine totali in '{filename}': {len(dati_esistenti)}")
        print("-" * 30)

    except Exception as e:
        print(f"Errore: {e}")