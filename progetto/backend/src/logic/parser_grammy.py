import os
import html
import re
import tempfile
import asyncio
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def get_domain(url: str) -> str:
    """ Restituisce il dominio in minuscolo da un URL dato """
    parsed = urlparse(url)
    return parsed.netloc.lower()

def clean_grammy_markdown(md_text: str) -> str:
    if not md_text: return ""
    
    md_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', md_text)
    
    lines = md_text.split('\n')
    clean_lines = []
    blacklist = ["read more", "watch:", "listen:", "photo by", "getty images", "related:", "share this", "subscribe", "newsletter", "twitter", "facebook"]
    
    for line in lines:
        l_str = line.strip()
        if not l_str:
            continue

        lower_line= l_str.lower()

        if len(l_str) < 150 and any(social in lower_line for social in ["twitter", "facebook", "whatsapp", "copy link"]):
            continue
            # m
        if len(l_str) < 200 and any(bad in lower_line for bad in blacklist):
            continue
            
        if re.match(r'^(top list|top feature)', l_str, re.IGNORECASE):
            continue
            
        clean_lines.append(l_str)
            
    return "\n\n".join(clean_lines)

async def parser_grammy(url: str, html_raw: str = None) -> dict:

    """
    Esegue il parsing specifico per grammy.com.
    Acquisizione sia tramite URL sia tramite HTML locale (se presente)
    """       
    browser_cfg = BrowserConfig(headless=True, extra_args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
        

    # configurazione del crawler
    crawler_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        css_selector="article", 
        excluded_tags=['header', 'footer', 'nav', 'aside', 'script', 'style', 'form'],
    )
    
    target_url = url
    temp_html_path = None
    
    # gestione del parsing di HTML diretto
    if html_raw:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as f:
            f.write(html_raw)
            temp_html_path = f.name
        target_url = f"file://{temp_html_path}"
        
    try:    
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            # processo di acquisizione
            result = await crawler.arun(url=target_url, config=crawler_cfg)
            if not result.success:
                raise Exception(f"Errore durante il crawling: {result.error_message}")

            # estrazione dinamica del titolo
            title = result.metadata.get("title") if result.metadata else None        
            md_text = result.markdown or "" # evita che il titolo sia None
            
            if not title or title.lower() == "grammy":
                h_match = re.search(r'^#+\s+(.*)', md_text, re.MULTILINE)
                if h_match:
                    title = h_match.group(1).strip()

            if title:
                title = html.unescape(title)
                title = title.split('|')[0].split('—')[0].strip()
            else:
                title = "Grammy Resource"
            
            return {
                    "url": url, 
                    "domain": get_domain(url), 
                    "title": title,
                    "html_text": result.html, 
                    "parsed_text": md_text
                }
    finally:
        if temp_html_path and os.path.exists(temp_html_path):
            os.remove(temp_html_path)

# ==========================================
# TEST VISIVO VELOCE
# ==========================================
if __name__ == "__main__":
    async def test_veloce():
        test_url = "https://www.grammy.com/news/heavy-metal-music-latin-america-history/" 
        print(f"Test in corso su: {test_url}")
        res = await parser_grammy(test_url)
        print("\n--- TESTO PARSATO ---")
        print(res['parsed_text'])

    asyncio.run(test_veloce())