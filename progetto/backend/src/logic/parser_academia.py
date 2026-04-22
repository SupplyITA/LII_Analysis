import asyncio
import json
import os
import re
from urllib.parse import urlparse
import tempfile
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode


def get_domain(url: str) -> str:   
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain

def clean_academia_markdown(md_text: str) -> str:
    """Pulisce il markdown usando solo RegEx e logica sulle stringhe."""
    if not md_text:
        return "Contenuto non individuato."

    md_text = re.sub(r'!\[.*?\]\(.*?\)', '', md_text)
    
    md_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', md_text)

    md_text = re.sub(r'(?i)(\bread more\b|\bcontinue reading\b|\.\.\.more)', '', md_text)

    lines = md_text.split('\n')
    clean_lines = []
    
    blacklist = [
        "download pdf", "related papers", "cookie policy", "privacy policy", 
        "log in", "sign up", "loading preview", "save to library", 
        "view full text", "skip to main content", "search academia", 
        "terms of use", "academia.edu"
    ]
    
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
        if any(bad_word in line_str.lower() for bad_word in blacklist):
            continue
        if len(line_str) > 0 or line_str.startswith('#'):
            clean_lines.append(line_str)

    return "\n\n".join(clean_lines)


async def parser_academia(url: str, html_raw: str = None) -> dict:

    browser_cfg = BrowserConfig(
        headless=True,
        extra_args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
    )
    crawler_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        css_selector="main", 
        excluded_tags=['header', 'footer', 'nav', 'aside', 'script', 'style', 'form']
    )

    target_url = url
    temp_html_path = None

    if html_raw:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as f:
            f.write(html_raw)
            temp_html_path = f.name
        target_url = f"file://{temp_html_path}"

    try:
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            
            
            result = await crawler.arun(url=target_url, config=crawler_cfg)

            if not result.success:
                raise Exception(f"Crawl fallito: {result.error_message}")

            title = "Academia Paper"
            title_match = re.search(r'<title>(.*?)</title>', result.html, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).replace(" | Academia.edu", "").strip()
                # Rimuove (PDF), (DOC) o (DOCX) all'inizio del titolo (case-insensitive)
                title = re.sub(r'^\s*\((?:PDF|DOC|DOCX)\)\s*', '', title, flags=re.IGNORECASE).strip()

            return {
                "url": url, 
                "domain": "www.academia.edu", 
                "title": title,
                "html_text": result.html,
                "parsed_text": clean_academia_markdown(result.markdown)
            }
    finally:
        if temp_html_path and os.path.exists(temp_html_path):
            os.remove(temp_html_path)   
