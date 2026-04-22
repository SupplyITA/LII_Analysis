import asyncio
import json
import os
import html # AGGIUNTA !!!
import re # AGGIUNTA !!!
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def get_domain(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.lower()

async def parser_grammy(url: str, html_raw: str = None) -> dict:
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

        # TITOLO ESTRATTO IN MANIERA DINAMICA - PROVA!!!!!!!
        title = result.metadata.get("title") if result.metadata else None        
        
        if not title or title.lower() == "grammy":
            h_match = re.search(r'^#+\s+(.*)', result.markdown, re.MULTILINE)
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
                "parsed_text": result.markdown
            }
        

    
if __name__ == "__main__":
    test_url = "https://www.grammy.com/artists/lady-gaga/3611" 
   
    mio_gold_text_manuale = '''
Born Stefani Joanne Angelina Germanotta on March 28, 1986, in New York City, New York.

Lady Gaga’s debut album, 2008’s The Fame, reached No. 2 on the Billboard 200 and featured a pair of No. 1 singles: “Just Dance” and “Poker Face.”

Gaga won her first two GRAMMYs at the 52nd GRAMMY Awards for Best Dance Recording (“Poker Face”) and Best Dance/Electronic Album (The Fame). She also made her GRAMMY stage debut that year, performing a medley that included “Poker Face,” “Speechless,” and “Your Song” in a duet with Elton John.

She dove into the world of jazz with Tony Bennett on the GRAMMY-winning albums Cheek to Cheek (2014) and Love for Sale (2021). Her 2020 dance-pop album, Chromatica, featured the chart-topping duet “Rain on Me” with Ariana Grande. Her latest solo studio album, Mayhem (2025), features the global hit "Die with a Smile" with Bruno Mars.

Did you know? As a teenager, Lady Gaga honed her singing by working with vocal coach Don Lawrence.

Gaga performed “You’ve Got A Friend” at the 2014 MusiCares Person of the Year tribute honoring Carole King. In 2016, the GRAMMY Museum honored her with the Jane Ortner Artist Award for her support of the arts and music education.

In 2011, Lady Gaga founded the Born This Way Foundation, an organization dedicated to supporting the wellness of young people.
'''
   
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