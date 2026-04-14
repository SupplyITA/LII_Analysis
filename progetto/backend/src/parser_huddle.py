import asyncio
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def clean_huddle_content(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    # In WordPress il contenuto è solitamente in entry-content o article
    content = soup.find("div", {"class": "entry-content"}) or soup.find("article")
    
    if not content: return ""

    # Rimuoviamo social sharing, pubblicità e banner correlati
    for noise in content.select('.sharedaddy, .jp-relatedposts, .ad-unit, script, style'):
        noise.decompose()

    # Link in Markdown
    for a in content.find_all('a', href=True):
        link_text = a.get_text(strip=True)
        if link_text:
            a.replace_with(f"[{link_text}]({a['href']})")

    parts = []
    for tag in content.find_all(['h2', 'h3', 'p', 'table']):
        if tag.name == 'table':
            parts.append(f"\n| {tag.get_text(' | ', strip=True)} |\n")
        else:
            text = tag.get_text(strip=True)
            if text:
                prefix = "## " if tag.name == 'h2' else "### " if tag.name == 'h3' else ""
                parts.append(f"{prefix}{text}")

    return "\n\n".join(parts)

async def parse_huddle(url: str) -> dict:
    browser_cfg = BrowserConfig(headless=True)
    crawler_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url=url, config=crawler_cfg)
        if not result.success: raise Exception(f"Errore Huddle: {result.error_message}")

        soup = BeautifulSoup(result.html, "html.parser")
        title = soup.find("h1", {"class": "entry-title"}) or soup.find("h1")
        title_text = title.get_text().strip() if title else "Huddle Article"

        return {
            "url": url,
            "domain": "huddle.org",
            "title": title_text,
            "html_text": result.html,
            "parsed_text": clean_huddle_content(result.html)
        }

if __name__ == "__main__":
    URL = "https://www.huddle.org/2024/09/detroit-per-i-numeri-tampa-per-il-risultato-tampa-bay-buccaneers-vs-detroit-lions-20-16/"
    res = asyncio.run(parse_huddle(URL))
    print(f"TITOLO: {res['title']}\n\nESTRATTO:\n{res['parsed_text'][:1000]}...")