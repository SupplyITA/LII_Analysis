import asyncio
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
# in ordine sotto: motore del crawler, configurazione browser, configurazione request, modalità di cache


def get_domain(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.lower()


def clean_wikipedia_content(html: str) -> str:
    """Estrae solo il contenuto informativo dell'articolo."""
    if not html:
        return ""
    
    soup = BeautifulSoup(html, "html.parser")
    
    content = soup.find("div", {"id": "mw-content-text"})
    if not content:
        #fallback se non trova il div specifico
        content = soup.find("main") or soup.body
        if not content: return ""

    #rimuoviamo tutto quello che non ci interessa
    for element in content.select('table, .infobox, .reflist, .navbox, .mw-editsection, .ambox, .mw-jump-link, .metadata, sup.reference'):
        element.decompose()

    parts = []
    # Prendiamo solo i titoli di sezione e i paragrafi
    for tag in content.find_all(['h2', 'h3', 'p']):
        text = tag.get_text().strip()
        if text:
            if tag.name == 'h2':
                # Puliamo i titoli
                clean_text = text.split('[')[0].strip()
                parts.append(f"## {clean_text}")
            elif tag.name == 'h3':
                clean_text = text.split('[')[0].strip()
                parts.append(f"### {clean_text}")
            else:
                parts.append(text)

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

        # Estrae il testo pulito passando l'html completo alla tua funzione
        parsed_text = clean_wikipedia_content(html_grezzo)

        return {
            "url": url,
            "domain": get_domain(url),
            "title": title,
            "html_text": html_grezzo,
            "parsed_text": parsed_text
        }
        
        # result.success        → True se il crawl è andato a buon fine
        # result.error_message  → messaggio d'errore in caso di fallimento
        # result.markdown       → testo in Markdown, pronto per LLM e RAG
        # result.cleaned_html   → HTML ripulito da script, stili e rumore
        # result.html           → HTML completo della pagina (non ripulito)

# test
if __name__ == "__main__":
    # Test con Minerva (come suggerito dalle slide 20)
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

