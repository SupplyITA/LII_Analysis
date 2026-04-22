import asyncio
import json
import os
import re
import html
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def get_domain(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain

def clean_huddle_markdown(md_text: str) -> str:
    """Pulisce il markdown rimuovendo rumore tipico di Huddle."""
    if not md_text: return ""
    # Rimuove link mantenendo il testo
    md_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', md_text)
    
    lines = md_text.split('\n')
    clean_lines = []
    blacklist = ["pubblicità", "condividi", "facebook", "twitter", "adsbygoogle", "ph.credits"]
    
    for line in lines:
        l_str = line.strip()
        if l_str and not any(bad in l_str.lower() for bad in blacklist):
            if l_str.startswith('#') or len(l_str) > 30:
                clean_lines.append(l_str)
    return "\n\n".join(clean_lines)    

async def parser_huddle(url: str, html_raw: str = None) -> dict:
    browser_cfg = BrowserConfig(headless=True)
    crawler_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        css_selector="article", 
        excluded_selectors=".share-buttons, .stream-item, .post-meta"    
    )

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        target = f"raw:{html_raw}" if html_raw else url
        result = await crawler.arun(url=target, config=crawler_cfg)
        
        if not result.success:
            raise Exception(f"Errore Huddle: {result.error_message}")
        
        # Estrazione titolo dinamica
        title = "Huddle Article"
        title_match = re.search(r'<title[^>]*>(.*?)</title>', result.html, re.IGNORECASE | re.S)
        if title_match:
            title = html.unescape(title_match.group(1)).split('|')[0].split('—')[0].strip()
        
        if (title.lower() == "huddle" or "huddle" in title.lower()) and result.markdown:
            h1_match = re.search(r'^#\s+(.*)', result.markdown, re.MULTILINE)
            if h1_match: title = h1_match.group(1).strip()
        
        return {
            "url": url,
            "domain": get_domain(url),
            "title": title,
            "html_text": result.html,
            "parsed_text": clean_huddle_markdown(result.markdown)
        }

if __name__ == "__main__":
    test_url = "" 
   
    mio_gold_text_manuale = """ 

    """
   
    filename = "huddle.org_gs.json"
   
    try:
        print(f"Scaricamento di {test_url} in corso...")
        res = asyncio.run(parser_huddle(test_url))
        
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
        print(f"Errore durante l'esecuzione: {e}")