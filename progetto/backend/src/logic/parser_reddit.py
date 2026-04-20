import asyncio
import json
import os
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def clean_reddit_content(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    parts = []
    
    post = soup.find("shreddit-post")
    if post:
        parts.append("## Original Post")
        content_div = post.find("div", {"slot": "text-body"})
        if content_div:
            # Trasformiamo i link del post in Markdown
            for a in content_div.find_all('a', href=True):
                link_text = a.get_text(strip=True)
                if link_text:
                    a.replace_with(f"[{link_text}]({a['href']})")
            parts.append(content_div.get_text("\n", strip=True))

    #estrazione dei commenti

    comments = soup.find_all("shreddit-comment")
    if comments:
        parts.append("\n---\n## Top Comments")
        
        for i, comment in enumerate(comments):
            #limitiamo il numero dei commenti a 10 per evitare di sovraccaricare l'output
            if i >= 10: break 
            
            comment_body = comment.find("div", {"slot": "comment"})
            if comment_body:
                text = comment_body.get_text(" ", strip=True)
                
                if text and len(text) > 5:
                    parts.append(f"- {text}")

    return "\n\n".join(parts)
async def parser_reddit(url: str) -> dict:
    browser_cfg = BrowserConfig(headless=True)
    crawler_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url=url, config=crawler_cfg)
        if not result.success:
            raise Exception(f"Errore Reddit: {result.error_message}")

        full_html = result.html
        soup = BeautifulSoup(full_html, "html.parser")
        
        # Estrazione Titolo (cercando nel tag h1 o nel componente shreddit)
        title_tag = soup.find("h1")
        title = title_tag.get_text().strip() if title_tag else "Reddit Post"

        return {
            "url": url,
            "domain": "reddit.com",
            "title": title,
            "html_text": full_html,
            "parsed_text": clean_reddit_content(full_html)
        }
# --- BLOCCO DI TEST PER REDDIT ---
if __name__ == "__main__":

    test_url = "https://en.wikipedia.org/wiki/Artemis_II" 
   
    mio_gold_text_manuale = """
"""
   
    filename = "en.wikipedia.org_gs.json"
   
    try:
        res = asyncio.run(parser_reddit(test_url))
        

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