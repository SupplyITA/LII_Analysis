import asyncio
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def clean_reddit_content(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    parts = []
    
    # 1. Estrazione del Post Originale (OP)
    post = soup.find("shreddit-post")
    if post:
        parts.append("## Original Post")
        content_div = post.find("div", {"slot": "text-body"})
        if content_div:
            # Trasformiamo i link del post in Markdown
            for a in content_div.find_all('a', href=True):
                link_text = a.get_text(strip=True)
                if link_text:
                    a.replace_with(f"[{link_text}]({a['href']})")
            parts.append(content_div.get_text("\n", strip=True))

    # 2. Estrazione dei Commenti
    # Reddit usa il tag <shreddit-comment> per i singoli commenti
    comments = soup.find_all("shreddit-comment")
    if comments:
        parts.append("\n---\n## Top Comments")
        
        for i, comment in enumerate(comments):
            # Limitiamo a un numero ragionevole di commenti (es. i primi 10) 
            # per evitare di avere un documento troppo lungo e dispersivo
            if i >= 10: break 
            
            # Il testo del commento è solitamente dentro un div con slot="comment"
            comment_body = comment.find("div", {"slot": "comment"})
            if comment_body:
                # Puliamo il testo del commento
                text = comment_body.get_text(" ", strip=True)
                # Rimuoviamo eventuali testi "Reply", "Give Award" ecc. se presenti
                if text and len(text) > 5: # Ignoriamo commenti troppo brevi o vuoti
                    parts.append(f"- {text}")

    return "\n\n".join(parts)
async def parse_reddit(url: str) -> dict:
    browser_cfg = BrowserConfig(headless=True)
    crawler_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url=url, config=crawler_cfg)
        if not result.success:
            raise Exception(f"Errore Reddit: {result.error_message}")

        full_html = result.html
        soup = BeautifulSoup(full_html, "html.parser")
        
        # Estrazione Titolo (cercando nel tag h1 o nel componente shreddit)
        title_tag = soup.find("h1")
        title = title_tag.get_text().strip() if title_tag else "Reddit Post"

        return {
            "url": url,
            "domain": "reddit.com",
            "title": title,
            "html_text": full_html,
            "parsed_text": clean_reddit_content(full_html)
        }
# --- BLOCCO DI TEST PER REDDIT ---
if __name__ == "__main__":

    URL_TEST = "https://www.reddit.com/r/linux4noobs/comments/103afgw/what_is_latex_and_how_does_one_get_started/?tl=it" 

    try:
        res = asyncio.run(parse_reddit(URL_TEST))
        print(f"TITOLO POST: {res['title']}\n")
        print("ESTRATTO (POST + COMMENTI):")
        print(res['parsed_text'][:1500] + "...") 
    except Exception as e:
        print(f"Errore durante il test Reddit: {e}")