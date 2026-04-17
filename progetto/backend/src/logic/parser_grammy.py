import asyncio
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def clean_grammy_content(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    
    content = soup.select_one('.article-body') or \
              soup.select_one('.news-story-content') or \
              soup.select_one('article') or \
              soup.select_one('.content')

    if not content:
        content = soup.find('main')

    if not content: return "Contenuto non individuato."

    for noise in content.select('script, style, .social-share, .image-caption, .photo-credits, .video-container, .related-links, footer, header'):
        noise.decompose()

    parts = []
    for p in content.find_all(['p', 'h2', 'h3']):
        text = p.get_text(separator=" ", strip=True)
        if len(text) > 40:
            parts.append(text)

    return "\n\n".join(parts)

async def parse_grammy(url: str) -> dict:
    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        result = await crawler.arun(url=url, config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS))
        soup = BeautifulSoup(result.html, "html.parser")
        title = soup.find("h1").get_text().strip() if soup.find("h1") else "Grammy News"
        return {
            "url": url, "domain": "grammy.com", "title": title,
            "html_text": result.html, "parsed_text": clean_grammy_content(result.html)
        }
    
if __name__ == "__main__":
    URL_TEST = "https://www.grammy.com/news/mastodon-reach-new-levels-of-heavy-on-emperor-of-sand"
    
    print(f"--- TEST GRAMMY: {URL_TEST} ---")
    try:
        res = asyncio.run(parse_grammy(URL_TEST))
        print(f"TITOLO: {res['title']}")
        print(f"DOMINIO: {res['domain']}")
        print("-" * 30)
        print("ESTRATTO (Primi 500 caratteri):")
        # Mostra l'estratto; se è vuoto segnala un problema
        output = res['parsed_text'][:500] if res['parsed_text'] else "ESTRATTO VUOTO - Controlla i selettori"
        print(output)
        print("-" * 30)
        print("Test completato.")
    except Exception as e:
        print(f"Errore durante il test: {e}")