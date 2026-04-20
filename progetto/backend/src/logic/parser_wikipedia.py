import asyncio
import json
import os
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def get_domain(url: str) -> str:

    parsed = urlparse(url)
    return parsed.netloc.lower()

async def parser_wikipedia(url: str, html_raw: str = None) -> dict:

    browser_cfg = BrowserConfig(headless=True)
    
    crawler_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        css_selector="#mw-content-text",
        excluded_tags=[
            '.infobox', '.reflist', '.navbox', '.mw-editsection', 
            '.reference', '.metadata', '#See_also', '#References', 
            '#Further_reading', '#External_links'
        ]
    )

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        target = f"raw:{html_raw}" if html_raw else url
        
        result = await crawler.arun(url=target, config=crawler_cfg)

        if not result.success:
            raise Exception(f"Errore durante il crawling: {result.error_message}")

        title = result.metadata.get('title', 'No Title Found') if result.metadata else "No Title Found"

        return {
            "url": url,
            "domain": get_domain(url),
            "title": title,
            "html_text": result.html,
            "parsed_text": result.markdown  
        }

async def aggiorna_gold_standard(filename):
    """Aggiorna il file JSON esistente mantenendo i gold_text manuali."""
    if not os.path.exists(filename):
        print(f"Errore: Il file {filename} non esiste.")
        return

    with open(filename, "r", encoding="utf-8") as f:
        pagine_vecchie = json.load(f)

    pagine_aggiornate = []
    
    for entry in pagine_vecchie:
        print(f"Aggiornamento per: {entry['url']}...")
        try:
            res = await parser_wikipedia(entry['url'])
            
            nuova_entry = {
                "url": entry['url'],
                "domain": entry['domain'],
                "title": res['title'],
                "html_text": res['html_text'], 
                "gold_text": entry['gold_text'] 
            }
            pagine_aggiornate.append(nuova_entry)
        except Exception as e:
            print(f"Errore su {entry['url']}: {e}. Mantengo il vecchio.")
            pagine_aggiornate.append(entry)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(pagine_aggiornate, f, indent=4, ensure_ascii=False)
    
    print(f"\nTutte le {len(pagine_aggiornate)} pagine sono state aggiornate con successo.")

if __name__ == "__main__":
    asyncio.run(aggiorna_gold_standard("en.wikipedia.org_gs.json"))