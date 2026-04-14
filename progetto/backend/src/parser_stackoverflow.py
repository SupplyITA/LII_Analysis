import asyncio
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def get_domain(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.lower()

def clean_post_body(post_body_div):
    """Trasforma un div di SO in Markdown pulito con blocchi di codice e link."""
    if not post_body_div: return ""

    # 1. Rimuoviamo i pulsanti "Copy" che sporcano il testo
    for btn in post_body_div.select('.js-code-copy-container, .d-none'):
        btn.decompose()

    # 2. Trasformiamo i blocchi di codice <pre><code> in Markdown ```
    for pre in post_body_div.find_all('pre'):
        code = pre.find('code')
        if code:
            code_text = code.get_text()
            pre.replace_with(f"\n```cpp\n{code_text}\n```\n") # Usiamo cpp come default visto il tuo test

    # 3. Trasformiamo i link in Markdown [testo](url)
    for a in post_body_div.find_all('a', href=True):
        link_text = a.get_text(strip=True)
        href = a['href']
        if href.startswith('/'): href = f"https://stackoverflow.com{href}"
        if link_text:
            a.replace_with(f"[{link_text}]({href})")

    return post_body_div.get_text("\n", strip=True)

# Poi usa questa funzione dentro clean_stackoverflow_content:
def clean_stackoverflow_content(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    parts = []
    
    # Domanda
    question = soup.find("div", {"class": "js-post-body"}) # Il primo è solitamente la domanda
    if question:
        parts.append("## QUESTION")
        parts.append(clean_post_body(question))

    # Risposte
    answers = soup.select(".answer .js-post-body")
    if answers:
        parts.append("\n" + "="*20 + "\n## ANSWERS")
        for i, ans in enumerate(answers):
            parts.append(f"### Answer {i+1}")
            parts.append(clean_post_body(ans))
            parts.append("-" * 10)

    return "\n\n".join(parts)

async def parse_stackoverflow(url: str) -> dict:
    browser_cfg = BrowserConfig(headless=True)
    crawler_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url=url, config=crawler_cfg)
        if not result.success:
            raise Exception(f"Errore: {result.error_message}")

        full_html = result.html
        soup = BeautifulSoup(full_html, "html.parser")
        
        # Titolo della domanda
        title_tag = soup.find("h1", {"itemprop": "name"}) or soup.find("h1")
        title = title_tag.get_text().strip() if title_tag else "Stack Overflow Question"

        return {
            "url": url,
            "domain": get_domain(url),
            "title": title,
            "html_text": full_html,
            "parsed_text": clean_stackoverflow_content(full_html)
        }

# --- BLOCCO DI TEST ---
if __name__ == "__main__":
    # INSERISCI QUI IL LINK DI STACK OVERFLOW
    URL_TEST = "https://stackoverflow.com/questions/79925142/how-can-i-retrieve-the-fraction-of-functions-with-examples-purely-from-an-r-pack"
    #URL_TEST = "https://stackoverflow.com/questions/79925175/c26-reflection-how-to-actually-do-class-metaprogramming" 
    try:
        res = asyncio.run(parse_stackoverflow(URL_TEST))
        print(f"TITOLO: {res['title']}\n")
        print("ESTRATTO:")
        print(res['parsed_text'][:1000] + "...") # Primi 1000 caratteri
    except Exception as e:
            print(f"Errore durante il test: {e}")
