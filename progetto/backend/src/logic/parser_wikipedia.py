import os
import tempfile
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
import re
import json, asyncio

def get_domain(url: str) -> str:
    """ Restituisce il dominio in minuscolo da un URL dato """
    parsed = urlparse(url)
    return parsed.netloc.lower()

async def parser_wikipedia(url: str, html_raw: str = None) -> dict:
    """
    Esegue il parsing specifico per wikipedia.
    Acquisizione sia tramite URL sia tramite HTML locale (se presente)
    """
    
    browser_cfg = BrowserConfig(headless=True, extra_args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
    
    # rimuove elementi non informativi 
    js_script = """
    let pageTitle = "No Title Found";
    let heading = document.getElementById('firstHeading');
    if (heading) {
        pageTitle = heading.innerText;
    } else if (document.title) {
        pageTitle = document.title.replace(' - Wikipedia', '');
    }

    document.querySelectorAll('sup, nav, footer, script, style, .infobox, .reflist, .navbox, .mw-editsection, .reference, .metadata, .printfooter').forEach(el => el.remove());
    let seeAlso = document.getElementById('See_also');
    if (seeAlso && seeAlso.parentNode) {
        while (seeAlso.parentNode.nextSibling) { seeAlso.parentNode.nextSibling.remove(); }
        seeAlso.parentNode.remove();
    }

    let content = document.querySelector('#mw-content-text');
    if (content) {
        content.setAttribute('data-wiki-title', pageTitle.replace(/"/g, '&quot;'));
    }
    """
    # configurazione del crawler
    crawler_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, css_selector="#mw-content-text", js_code=js_script)

    # gestione del parsing di HTML diretto
    target_url = url
    temp_html_path = None
    if html_raw:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as f:
            f.write(html_raw)
            temp_html_path = f.name
        target_url = f"file://{temp_html_path}"

    try:
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            # processo di acquisizione
            result = await crawler.arun(url=target_url, config=crawler_cfg)
            if not result.success:
                raise Exception(f"Errore durante il crawling: {result.error_message}")

            # estrazione dinamica del titolo
            title = "No Title Found"
            if result.html:
                # Estrae l'attributo che abbiamo iniettato tramite JavaScript
                match = re.search(r'data-wiki-title="([^"]+)"', result.html)
                if match:
                    title = match.group(1).replace('&quot;', '"')
                    
            # Fallback di sicurezza nel caso in cui stia usando il comportamento base
            if title == "No Title Found" and result.metadata:
                title = result.metadata.get("title", "No Title Found")
            
            return {
                "url": url,
                "domain": get_domain(url),
                "title": title,
                "html_text": result.html,
                "parsed_text": result.markdown or ""
            }
    finally:
        if temp_html_path and os.path.exists(temp_html_path):
            os.remove(temp_html_path)

# ----------------------- aggiunta URL(o) -----------------------
if __name__ == "__main__":

    test_url = "" 
    
    mio_gold_text_manuale = """
"""

    filename = "progetto/gs_data/en.wikipedia.org_gs.json"
   
    async def run():
        try:
            print(f"Eseguo parser su: {test_url}")
            res = await parser_wikipedia(test_url)
            print(f"DEBUG - Titolo estratto: {res['title']}")
            
            nuova_entry = {
                "url": res['url'],
                "domain": res['domain'],
                "title": res['title'],
                "html_text": res['html_text'], 
                "gold_text": mio_gold_text_manuale.strip()
            }

            dati_esistenti = []
            if os.path.exists(filename):
                with open(filename, "r", encoding="utf-8") as f:
                    try:
                        dati_esistenti = json.load(f)
                    except:
                        dati_esistenti = []
            
            # verifica duplicati
            if not any(e['url'] == nuova_entry['url'] for e in dati_esistenti):
                dati_esistenti.append(nuova_entry)
                # crea la cartella se non esiste
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(dati_esistenti, f, indent=4, ensure_ascii=False)
                print(f"SUCCESSO: Pagina aggiunta a {filename}.")
            else:
                print("URL già presente nel file. Salto.")

        except Exception as e:
            print(f"Errore durante l'esecuzione: {e}")

    asyncio.run(run())