import asyncio
import json
import os
import re
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def get_domain(url: str) -> str:   
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain

def clean_academia_markdown(md_text: str) -> str:
    """Pulisce il markdown usando solo RegEx e logica sulle stringhe."""
    if not md_text:
        return "Contenuto non individuato."

    md_text = re.sub(r'!\[.*?\]\(.*?\)', '', md_text)
    
    md_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', md_text)

    md_text = re.sub(r'(?i)(\bread more\b|\bcontinue reading\b|\.\.\.more)', '', md_text)

    lines = md_text.split('\n')
    clean_lines = []
    
    blacklist = [
        "download pdf", "related papers", "cookie policy", "privacy policy", 
        "log in", "sign up", "loading preview", "save to library", 
        "view full text", "skip to main content", "search academia", 
        "terms of use", "academia.edu"
    ]
    
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
        if any(bad_word in line_str.lower() for bad_word in blacklist):
            continue
        if len(line_str) > 0 or line_str.startswith('#'):
            clean_lines.append(line_str)

    return "\n\n".join(clean_lines)


async def parser_academia(url: str, html_raw: str = None) -> dict:
    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        
        target = f"raw:{html_raw}" if html_raw else url
        
        result = await crawler.arun(url=target, config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS))

        if not result.success:
            raise Exception(f"Crawl fallito: {result.error_message}")

        title = "Academia Paper"
        title_match = re.search(r'<title>(.*?)</title>', result.html, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).replace(" | Academia.edu", "").strip()
            # Rimuove (PDF), (DOC) o (DOCX) all'inizio del titolo (case-insensitive)
            title = re.sub(r'^\s*\((?:PDF|DOC|DOCX)\)\s*', '', title, flags=re.IGNORECASE).strip()

        return {
            "url": url, 
            "domain": get_domain(url), 
            "title": title,
            "html_text": result.html,
            "parsed_text": clean_academia_markdown(result.markdown)
        }
        
        
    
if __name__ == "__main__":

    test_url = "https://www.academia.edu/15509220/What_Is_Software_Engineering#key-takeaways" 
   
    mio_gold_text_manuale = """A later translation (2015) of the article in Russian published in 1990. The article proposes an approach to defining a set of basic notions for subject area of software engineering discipline. The set of notions is intended to serve as a basis for detection and correction of some widespread conceptual mistakes in the efforts aimed at improving the quality and work productivity in creation and operation of software.
"""
   
    filename = "academia.edu_gs.json"
   
    try:
        res = asyncio.run(parser_academia(test_url))
        
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
            
        print(f"SUCCESSO: Pagina aggiunta al file {filename}.")

    except Exception as e:
        print(f"Errore durante il test: {e}")