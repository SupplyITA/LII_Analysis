import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def main():
    # configura il browser (headless = senza finestra visibile)
    browser_cfg = BrowserConfig(headless=False)

    # configura la richiesta (BYPASS = scarica sempre dalla rete, ignora cache)
    crawler_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS) '''css_selector="#bodyContent")'''

    # apre il browser e lo chiude automaticamente alla fine del blocco
    async with AsyncWebCrawler(config=browser_cfg) as crawler:

        # visita la pagina e aspetta che il crawl sia completato
        result = await crawler.arun(
            url="https://en.wikipedia.org/wiki/Horse",
            config=crawler_cfg
        )

        

        # result.success        → True se il crawl è andato a buon fine
        # result.error_message  → messaggio d'errore in caso di fallimento
        # result.markdown       → testo in Markdown, pronto per LLM e RAG
        # result.cleaned_html   → HTML ripulito da script, stili e rumore
        # result.html           → HTML completo della pagina (non ripulito)
        print(result.markdown)

# avvia il programma asincrono
asyncio.run(main())