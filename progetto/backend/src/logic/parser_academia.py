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

    test_url = "https://www.academia.edu/37086183/Computer_Science_vs_Computer_Engineering?sm=b" 
   
    mio_gold_text_manuale = """As technology evolves and spins off into highly specialized fields, so do the careers and advanced degrees that support it. As these degrees and specialties increasingly narrow their areas of focus, it can be helpful to understand how they play into the larger technology landscape by breaking them down into two core curriculum: computer science and computer engineering. And while there's common ground between them, knowing where these two fields both overlap and diverge is a good place to start. THE THEORETICAL: COMPUTER SCIENCE Computer science is primarily concerned with computational theory, namely the architecture, data, algorithms, and programming languages that comprise the software that's run on a computer. Computer scientists are focused on things like code, algorithms, artificial intelligence, database design, and software design. Therefore, computer scientists are scientists and mathematicians who develop ways to process, interpret, store, communicate, and secure data. THE PRACTICAL: COMPUTER ENGINEERING Computer engineering takes that theory and applies to to real life. Essentially it's computer science put into action, married up with the field of electrical engineering. If computer science happens in code, in the abstract, computer engineering often happens in the lab. It involves designing and prototyping the tiny circuits and processing units that bridge the computer's hardware components with the software it's running—whether the implementations are embedded systems, microprocessors, networked IoT devices, or " smart " anything. Therefore, computer engineers are electrical engineers who specialize in software design, hardware design, or systems design that integrates both. WHERE BOTH ENDS MEET: SOFTWARE ENGINEERING You can't talk about computer science and computer engineering without touching on software engineering—the bridge between the two that provides the architecture for the instructions the hardware executes. A software engineer bridges both disciplines together, applying computer science theories to software. A software engineer gets even more hands-on with programming by translating those concepts into functional applications that leverage the hardware they run on.
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