import asyncio
import json
import os
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def clean_academia_content(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    
    for banner in soup.select('.cookie-policy, .consent-banner, #cookie-notice, .privacy-policy'):
        banner.decompose()

    
    content = soup.select_one('.abstract-text') or \
              soup.select_one('.p-about') or \
              soup.select_one('.work-show-full-text')
    
    if content:
        return "\n\n".join([p.get_text(strip=True) for p in content.find_all('p') if len(p.get_text()) > 20])

    fallback_texts = []
    for p in soup.find_all('p'):
        t = p.get_text(strip=True)
        if len(t) > 60 and "cookie" not in t.lower() and "privacy policy" not in t.lower():
            fallback_texts.append(t)
            
    return "\n\n".join(fallback_texts) if fallback_texts else "Contenuto non individuato."

async def parse_academia(url: str) -> dict:
    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        result = await crawler.arun(url=url, config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS))
        soup = BeautifulSoup(result.html, "html.parser")
        title = soup.find("h1").get_text().strip() if soup.find("h1") else "Academia Paper"
        return {
            "url": url, "domain": "academia.edu", "title": title,
            "html_text": result.html, "parsed_text": clean_academia_content(result.html)
        }
    
if __name__ == "__main__":

    test_url = "https://en.wikipedia.org/wiki/Artemis_II" 
   
    mio_gold_text_manuale = """
"""
   
    filename = "en.wikipedia.org_gs.json"
   
    try:
        res = asyncio.run(parse_academia(test_url))
        

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