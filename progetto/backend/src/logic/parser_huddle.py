import asyncio
import json
import os
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def get_domain(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.lower()

async def parser_huddle(url: str, html_raw: str = None) -> dict:
    browser_cfg = BrowserConfig(headless=True)
    
    crawler_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        css_selector="article", 
        excluded_tags=['header', 'footer', 'nav'] 
    )
    
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        target = f"raw:{html_raw}" if html_raw else url
        
        result = await crawler.arun(url=target, config=crawler_cfg)
        
        if not result.success:
            raise Exception(f"Errore durante il crawling: {result.error_message}")
        
        title = result.metadata.get('title', 'Titolo non trovato') if result.metadata else "Titolo non trovato"
        
        return {
            "url": url,
            "domain": get_domain(url),
            "title": title,
            "html_text": result.html,
            "parsed_text": result.markdown
        }

async def aggiorna_huddle_gs():
    filename = "huddle.org_gs.json"
    
    if not os.path.exists(filename):
        print(f"Errore: Il file {filename} non esiste. Assicurati di crearlo prima.")
        return

    with open(filename, "r", encoding="utf-8") as f:
        try:
            pagine_vecchie = json.load(f)
        except json.JSONDecodeError:
            pagine_vecchie = []

    pagine_aggiornate = []

    for entry in pagine_vecchie:
        print(f"Aggiornamento per: {entry['url']}...")
        try:
            res = await parser_huddle(entry['url'])
            
            nuova_entry = {
                "url": entry['url'],
                "domain": entry['domain'],
                "title": res['title'],
                "html_text": res['html_text'], 
                "gold_text": entry['gold_text']
            }
            pagine_aggiornate.append(nuova_entry)
        except Exception as e:
            print(f"Errore su {entry['url']}: {e}. Mantengo la vecchia entry.")
            pagine_aggiornate.append(entry)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(pagine_aggiornate, f, indent=4, ensure_ascii=False)
    
    print(f"\nFatto! {len(pagine_aggiornate)} pagine di Huddle aggiornate al nuovo formato.")

if __name__ == "__main__":
    asyncio.run(aggiorna_huddle_gs())