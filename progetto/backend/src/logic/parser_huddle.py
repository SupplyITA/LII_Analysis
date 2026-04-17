import asyncio
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def clean_huddle_content(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    content = soup.find("div", {"class": "entry-content"}) or soup.find("article")
    if not content: return ""
    for a in content.find_all('a', href=True):
        if a.get_text(strip=True): a.replace_with(f"[{a.get_text(strip=True)}]({a['href']})")
    parts = []
    for tag in content.find_all(['h2', 'h3', 'p', 'table']):
        if tag.name == 'table': parts.append(f"| {tag.get_text(' | ', strip=True)} |")
        else: parts.append(f"{'## ' if tag.name=='h2' else ''}{tag.get_text(strip=True)}")
    return "\n\n".join(parts)

async def parse_huddle(url: str) -> dict:
    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        result = await crawler.arun(url=url, config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS))
        soup = BeautifulSoup(result.html, "html.parser")
        title = soup.find("h1").get_text().strip()
        return {
            "url": url, "domain": "huddle.org", "title": title,
            "html_text": result.html, "parsed_text": clean_huddle_content(result.html)
        }
    
if __name__ == "__main__":
    URL_TEST = "https://www.huddle.org/2024/09/detroit-per-i-numeri-tampa-per-il-risultato-tampa-bay-buccaneers-vs-detroit-lions-20-16/"
    
    print(f"--- TEST HUDDLE: {URL_TEST} ---")
    try:
        res = asyncio.run(parse_huddle(URL_TEST))
        print(f"TITOLO: {res['title']}")
        print(f"DOMINIO: {res['domain']}")
        print("-" * 30)
        print("ESTRATTO (Primi 500 caratteri):")
        print(res['parsed_text'][:500])
        print("-" * 30)
        print("Test completato.")
    except Exception as e:
        print(f"Errore durante il test: {e}")