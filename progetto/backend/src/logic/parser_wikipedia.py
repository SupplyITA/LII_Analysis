import asyncio
import json
import os
import re
import mistune
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def remove_markdown(md: str) -> str:
    if not md: return ""
    html = mistune.html(md)
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(True):
        tag.unwrap()
    text = re.sub(r'[ \t]+', ' ', str(soup)) 
    text = re.sub(r'\n+', '\n', text) 
    return text.strip()

def get_domain(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.lower()

async def parser_wikipedia(url: str, html_raw: str = None) -> dict:
    browser_cfg = BrowserConfig(headless=True)
    
    # Solo tag HTML standard, per prevenire il crash 'Invalid expression'
    crawler_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        css_selector="#mw-content-text",
        excluded_tags=['sup', 'nav', 'footer', 'script', 'style']
    )

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        target = f"raw:{html_raw}" if html_raw else url
        result = await crawler.arun(url=target, config=crawler_cfg)

        if not result.success:
            raise Exception(f"Errore durante il crawling: {result.error_message}")

        title = result.metadata.get('title', 'No Title Found') if result.metadata else "No Title Found"
        
        md_text = result.markdown
        
        # Fallback se Crawl4AI fallisce la conversione Markdown
        if "Crawl4AI Error" in md_text or "Invalid expression" in md_text:
            soup = BeautifulSoup(result.html, "html.parser")
            content = soup.find(id="mw-content-text")
            if content:
                for tag in content.select('sup, nav, footer, script, style, .infobox, .reflist, .mw-editsection'):
                    tag.decompose()
                md_text = content.get_text(separator="\n\n", strip=True)

        return {
            "url": url,
            "domain": get_domain(url),
            "title": title,
            "html_text": result.html,
            "parsed_text": md_text
        }

async def aggiorna_gold_standard(filename):
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
            # Rigenera il Gold Standard basandosi sul vero output
            testo_gold_allineato = remove_markdown(res['parsed_text'])
            
            nuova_entry = {
                "url": entry['url'],
                "domain": entry['domain'],
                "title": res['title'],
                "html_text": res['html_text'], 
                "gold_text": testo_gold_allineato 
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