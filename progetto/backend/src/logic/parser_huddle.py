import asyncio
import json
import os
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def clean_huddle_content(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    content = soup.find("div", {"class": "entry-content"}) or soup.find("article")
    if not content: return ""
    for a in content.find_all('a', href=True):
        if a.get_text(strip=True): a.replace_with(f"[{a.get_text(strip=True)}]({a['href']})")
    parts = []
    for tag in content.find_all(['h2', 'h3', 'p', 'table']):
        if tag.name == 'table': parts.append(f"| {tag.get_text(' | ', strip=True)} |")
        else: parts.append(f"{'## ' if tag.name=='h2' else ''}{tag.get_text(strip=True)}")
    return "\n\n".join(parts)

async def parse_huddle(url: str) -> dict:
    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        result = await crawler.arun(url=url, config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS))
        soup = BeautifulSoup(result.html, "html.parser")
        title = soup.find("h1").get_text().strip()
        return {
            "url": url, "domain": "huddle.org", "title": title,
            "html_text": result.html, "parsed_text": clean_huddle_content(result.html)
        }
    
if __name__ == "__main__":

    test_url = "https://en.wikipedia.org/wiki/Artemis_II" 
   
    mio_gold_text_manuale = """
"""
   
    filename = "en.wikipedia.org_gs.json"
   
    try:
        res = asyncio.run(parse_huddle(test_url))
        

        nuova_entry = {
            "url": res['url'],
            "domain": res['domain'],
            "title": res['title'],
            "html_text": res['html_text'], 
            "gold_text": mio_gold_text_manuale.strip()
        }

        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                dati_esistenti = json.load(f)
        else:
            dati_esistenti = []

        # Aggiunge la pagina e salva
        dati_esistenti.append(nuova_entry)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(dati_esistenti, f, indent=4, ensure_ascii=False)

    except Exception as e:
        print(f"Errore durante il test: {e}")