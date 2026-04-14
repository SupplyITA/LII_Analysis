import asyncio
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def clean_academia_content(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    # Academia usa spesso 'main' o 'article' per il contenuto
    content = soup.find("div", {"id": "work_show_full_text"}) or soup.find("article") or soup.find("main")
    
    if not content: return "Contenuto testuale non individuato (possibile anteprima PDF)"

    # Rimozione rumore (pulsanti download, citazioni suggerite, sidebar)
    for noise in content.select('.download-button, .sidebar, .related-works, script, style'):
        noise.decompose()

    # Link in Markdown
    for a in content.find_all('a', href=True):
        link_text = a.get_text(strip=True)
        if link_text:
            a.replace_with(f"[{link_text}]({a['href']})")

    parts = []
    # Estrazione di titoli e paragrafi
    for tag in content.find_all(['h1', 'h2', 'h3', 'p']):
        text = tag.get_text(strip=True)
        if text:
            parts.append(text)

    return "\n\n".join(parts)

async def parse_academia(url: str) -> dict:
    browser_cfg = BrowserConfig(headless=True)
    crawler_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url=url, config=crawler_cfg)
        if not result.success: raise Exception(f"Errore Academia: {result.error_message}")

        soup = BeautifulSoup(result.html, "html.parser")
        title = soup.find("h1").get_text().strip() if soup.find("h1") else "Academia Paper"

        return {
            "url": url,
            "domain": "academia.edu",
            "title": title,
            "html_text": result.html,
            "parsed_text": clean_academia_content(result.html)
        }

if __name__ == "__main__":
    URL = "https://www.academia.edu/32357079/Non_Timber_Forest_Produce_Utilization_Distribution_and_Status_in_the_Khangchendzonga_Biosphere_Reserve_Sikkim_India"
    res = asyncio.run(parse_academia(URL))
    print(f"TITOLO: {res['title']}\n\nESTRATTO:\n{res['parsed_text'][:1000]}...")