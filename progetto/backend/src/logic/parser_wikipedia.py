import asyncio
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
# in ordine sotto: motore del crawler, configurazione browser, configurazione request, modalità di cache


def get_domain(url: str) -> str:
    """Estrae il dominio dall'URL """    
    parsed = urlparse(url)
    return parsed.netloc.lower()


def clean_wikipedia_content(html: str) -> str:
    """Estrae solo il contenuto informativo dell'articolo."""
    if not html:
        return ""
    
    soup = BeautifulSoup(html, "html.parser")
    
    content = soup.find("div", {"id": "mw-content-text"})
    if not content: return ""
        
    for element in content.select('.infobox, .reflist, .navbox, .mw-editsection, .ambox, .mw-jump-link, .metadata, sup.reference'):
        element.decompose()

    for a in content.find_all('a', href=True):
        link_text = a.get_text(strip=True)
        href = a['href']
        if href.startswith('/wiki/'):
            href = f"https://en.wikipedia.org{href}"
        if link_text:
            a.replace_with(f"[{link_text}]({href})")

    parts = []
    #cerchiamo i tag rilevanti includendo 'table' per le wiki-table
    for tag in content.find_all(['h2', 'h3', 'p', 'table']):
        if tag.name == 'table':
            table_text = tag.get_text(" | ", strip=True)
            if table_text:
                parts.append(f"\n| {table_text} |\n")
        elif tag.name in ['h2', 'h3']:
            title_text = tag.get_text().strip()
            clean_title = title_text.split('[')[0].strip()
            level = "##" if tag.name == 'h2' else "###"
            parts.append(f"{level} {clean_title}")
        else:
            p_text = tag.get_text().strip()
            if p_text:
                parts.append(p_text)

    return "\n\n".join(parts)

async def parse_wikipedia(url: str) -> dict:
    browser_cfg = BrowserConfig(headless=True)
    crawler_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)


    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url=url, config=crawler_cfg)

        if not result.success:
            raise Exception(f"Errore: {result.error_message}")

        html_grezzo = result.html
        soup = BeautifulSoup(html_grezzo, "html.parser")
        
        title_tag = soup.find("h1", {"id": "firstHeading"}) or soup.find("h1")
        title = title_tag.get_text().strip() if title_tag else "No Title Found"

        parsed_text = clean_wikipedia_content(html_grezzo)

        return {
            "url": url,
            "domain": get_domain(url),
            "title": title,
            "html_text": html_grezzo,
            "parsed_text": parsed_text
        }

# -- BLOCCO DI TEST LOCALE --        
if __name__ == "__main__":

    test_url = "https://en.wikipedia.org/wiki/Horse"
    try:
        res = asyncio.run(parse_wikipedia(test_url))
        print(f"URL: {res['url']}")
        print(f"TITOLO: {res['title']}")
        print(f"DOMINIO: {res['domain']}")
        print("-" * 30)
        print("ESTRATTO (primi 500 caratteri):")
        print(res['parsed_text'][:500])
        print("-" * 30)
        print("Parsing completato con successo!")
    except Exception as e:
        print(f"Si è verificato un errore: {e}")

