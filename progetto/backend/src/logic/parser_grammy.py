import asyncio
import os
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
import json
import os
import re

def clean_grammy_content(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    
    content = soup.select_one('.article-body') or \
              soup.select_one('.news-story-content') or \
              soup.select_one('article') or \
              soup.select_one('.content')

    if not content:
        content = soup.find('main')

    if not content: return "Contenuto non individuato."

    for noise in content.select('script, style, .social-share, .image-caption, .photo-credits, .video-container, .related-links, footer, header'):
        noise.decompose()

    parts = []
    for p in content.find_all(['p', 'h2', 'h3']):
        text = p.get_text(separator=" ", strip=True)
        if len(text) > 40:
            parts.append(text)

    return "\n\n".join(parts)

async def parse_grammy(url: str) -> dict:
    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        result = await crawler.arun(url=url, config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS))
        soup = BeautifulSoup(result.html, "html.parser")
        title = soup.find("h1").get_text().strip() if soup.find("h1") else "Grammy News"
        return {
            "url": url, "domain": "grammy.com", "title": title,
            "html_text": result.html, "parsed_text": clean_grammy_content(result.html)
        }
    
if __name__ == "__main__":

    test_url = "https://en.wikipedia.org/wiki/Artemis_II" 
   
    mio_gold_text_manuale = """
"""
   
    filename = "en.wikipedia.org_gs.json"
   
    try:
        res = asyncio.run(parse_grammy(test_url))
        

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