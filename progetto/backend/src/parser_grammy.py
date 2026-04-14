import asyncio
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def clean_grammy_content(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    # Grammy usa spesso classi come 'article-body' o simili
    content = soup.find("div", {"class": "article-body"}) or soup.find("div", {"class": "news-story-content"})
    
    if not content: return ""

    # Rimozione caption delle immagini, video embed e crediti fotografici
    for noise in content.select('.image-caption, .video-container, .photo-credits, script, style'):
        noise.decompose()

    # Link in Markdown
    for a in content.find_all('a', href=True):
        link_text = a.get_text(strip=True)
        if link_text:
            a.replace_with(f"[{link_text}]({a['href']})")

    parts = []
    for tag in content.find_all(['h2', 'h3', 'p']):
        text = tag.get_text(strip=True)
        if text:
            parts.append(text)

    return "\n\n".join(parts)

async def parse_grammy(url: str) -> dict:
    browser_cfg = BrowserConfig(headless=True)
    crawler_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url=url, config=crawler_cfg)
        if not result.success: raise Exception(f"Errore Grammy: {result.error_message}")

        soup = BeautifulSoup(result.html, "html.parser")
        # Il titolo è quasi sempre in un tag h1 con classe specifica
        title = soup.find("h1", {"class": "article-title"}) or soup.find("h1")
        title_text = title.get_text().strip() if title else "Grammy News"

        return {
            "url": url,
            "domain": "grammy.com",
            "title": title_text,
            "html_text": result.html,
            "parsed_text": clean_grammy_content(result.html)
        }

if __name__ == "__main__":
    URL = "https://www.grammy.com/news/mastodon-reach-new-levels-of-heavy-on-emperor-of-sand"
    res = asyncio.run(parse_grammy(URL))
    print(f"TITOLO: {res['title']}\n\nESTRATTO:\n{res['parsed_text'][:1000]}...")