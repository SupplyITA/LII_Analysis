import asyncio
import json
import os
import re
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def get_domain(url: str) -> str:   
    parsed = urlparse(url)
    return parsed.netloc.lower()

def clean_academia_markdown(md_text: str) -> str:
    """Pulisce il markdown usando solo RegEx e logica sulle stringhe."""
    if not md_text:
        return "Contenuto non individuato."

    
    md_text = re.sub(r'!\[.*?\]\(.*?\)', '', md_text)
    
    md_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', md_text)

    lines = md_text.split('\n')
    clean_lines = []
    blacklist = ["download pdf", "related papers", "cookie policy", "privacy policy", "log in", "sign up", "loading preview"]
    
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
        if any(bad_word in line_str.lower() for bad_word in blacklist):
            continue
        if len(line_str) > 50 or line_str.startswith('#'):
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

        return {
            "url": url, 
            "domain": get_domain(url), 
            "title": title,
            "html_text": result.html,
            "parsed_text": clean_academia_markdown(result.markdown)
        }
        
        
    
if __name__ == "__main__":

    test_url = "https://www.academia.edu/32357079/Non_Timber_Forest_Produce_Utilization_Distribution_and_Status_in_the_Khangchendzonga_Biosphere_Reserve_Sikkim_India" 
   
    mio_gold_text_manuale = """ountains are important repository of valuable resources and provide services to one third of the humanity living in this planet. Sikkim Himalaya is endowed with wide variety of non-timber forest produce (NTFP). M The ethno-cultural fabrics of this tiny state are rich in traditional practices. As a result, the people living in the Khangchendzonga complex use these natural resources in various ways for their subsistence. The study recorded 94 odd numbers of NTFPs from the area. Above 50% of these species are marketed in the local Hats with a minimum price, which otherwise have good potential in local economy. About 10% of the total species distribution was found to be a concern for conservation. Some of the high value medicinal plants have potential for value addition as well as domestication. Therefore, a strategic plan is needed for conservation of these valuable resources and for sustainable development.
The study documents 94 non-timber forest products (NTFPs) from the Khangchendzonga Biosphere Reserve.
Over 50% of the recorded NTFPs are marketed, primarily wild edibles and medicinal herbs.
Approximately 10% of NTFP species are conservation concerns, highlighting the need for strategic planning.
Rural communities in Sikkim rely heavily on NTFPs for subsistence and economic stability.
Training in NTFP cultivation and management is essential for sustainable development and biodiversity conservation.
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