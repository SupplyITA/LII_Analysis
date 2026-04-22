import asyncio
import json
import os
import html # AGGIUNTA !!!
import re # AGGIUNTA !!!
import tempfile
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
import mistune

def get_domain(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.lower()

async def parser_grammy(url: str, html_raw: str = None) -> dict:
    browser_cfg = BrowserConfig(
        headless=True,
        extra_args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
    )
    crawler_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        css_selector="main", 
        excluded_tags=['header', 'footer', 'nav', 'aside', 'script', 'style', 'form']
    )
    
    target_url = url
    temp_html_path = None

    if html_raw:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as f:
            f.write(html_raw)
            temp_html_path = f.name
        target_url = f"file://{temp_html_path}"
    try:    
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=target_url, config=crawler_cfg)
            
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
    finally:
        if temp_html_path and os.path.exists(temp_html_path):
            os.remove(temp_html_path)        


def remove_markdown(md: str) -> str:
    if not md: return ""
    html_str = mistune.html(md)
    soup = BeautifulSoup(html_str, "html.parser")
    for tag in soup.find_all(True):
        tag.unwrap()
    text = re.sub(r'[ \t]+', ' ', str(soup)) 
    text = re.sub(r'\n+', '\n', text) 
    return text.strip()

async def aggiorna_gold_standard(filename):
    if not os.path.exists(filename):
        print(f"Errore: Il file {filename} non esiste.")
        return
    with open(filename, "r", encoding="utf-8") as f:
        pagine_vecchie = json.load(f)

    pagine_aggiornate = []
    for entry in pagine_vecchie:
        try:
            # 1. Recuperiamo l'HTML GIA' SALVATO
            html_salvato = entry.get('html_text')
            
            if not html_salvato:
                print(f"Nessun HTML salvato trovato per {entry['url']}, salto...")
                pagine_aggiornate.append(entry)
                continue

            # 2. Passiamo l'html_raw al parser così NON va su internet
            res = await parser_grammy(entry['url'], html_raw=html_salvato) 
            
            testo_gold_allineato = remove_markdown(res['parsed_text'])
            nuova_entry = {
                "url": entry['url'],
                "domain": "grammy.com", # <-- METTI IL NOME ESATTO DEL DOMINIO QUI
                "title": res['title'],
                "html_text": res['html_text'], 
                "gold_text": testo_gold_allineato 
            }
            pagine_aggiornate.append(nuova_entry)
            print(f"OK: Aggiornato {entry['url']}")
        except Exception as e:
            print(f"Errore su {entry['url']}: {e}")
            pagine_aggiornate.append(entry)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(pagine_aggiornate, f, indent=4, ensure_ascii=False)
    print(f"Fatto! JSON aggiornato per {filename}.")


if __name__ == "__main__":
    asyncio.run(aggiorna_gold_standard("grammy.com_gs.json"))