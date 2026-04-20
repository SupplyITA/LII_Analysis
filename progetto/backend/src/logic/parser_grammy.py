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
    test_url = "https://www.grammy.com/news/mastodon-reach-new-levels-of-heavy-on-emperor-of-sand" 
   
    mio_gold_text_manuale = """ 
For a band with such dark thematic imagery, serious metal pedigree and crushing sonic heft, Mastodon sure can ham it up. One look at the music video for "Show Yourself," the lead single from their new album, Emperor Of Sand, will make their knack for comedy abundantly clear. However, one listen to the album will remind you that, musically at least, they're not messing around.

Mastodon's conceptually heavy Emperor of Sand follows 2014's Once More 'Round The Sun, which spawned a Best Metal Performance GRAMMY nomination for the song "High Road." Despite the band's jovial nature, the spirit and gravity of their new album was shaped largely by tragedy that touched their lives.

"Some of the closest people to us were in the middle of some battles with cancer and some heavy-duty illness," said drummer/vocalist Brann Dailor. "If we were open and honest with everyone about what the record was about, then we knew that it could maybe have a positive impact with someone else."

In this exclusive interview, Dailor and bassist/vocalist Troy Sanders talk about channeling personal pain and loss into artistic expression on Emperor Of Sand, how their common affinity and respect for Bay Area legends Neurosis brought them together, and what they enjoy most about the whirlwind of a new album-tour cycle.    
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