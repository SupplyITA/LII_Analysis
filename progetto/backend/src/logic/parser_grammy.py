import asyncio
import json
import os
import html
import re
import tempfile
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

def get_domain(url: str) -> str:
    """ Restituisce il dominio in minuscolo da un URL dato """
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain

def clean_grammy_markdown(md_text: str) -> str:
    if not md_text: return ""
    md_text = str(md_text)
    
    # Rimuove immagini e link mantenendo il testo leggibile
    md_text = re.sub(r'!\[.*?\]\(.*?\)', '', md_text)
    md_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', md_text)
    
    lines = md_text.split('\n')
    clean_lines = []

    # Blacklist per saltare singole righe inutili
    blacklist_exact = [
        "share this", "copy link", "subscribe", "newsletter", "twitter", "facebook", 
        "whatsapp", "instagram", "share on facebook", "share on x", "go back to news",
        "the grammys are more than just awards", "advancement", "music advocacy", "assistance",
        "empowering music makers through their creative journeys", "learn more",
        "defending creators’ rights while shaping a future of responsible innovation", "get involved",
        "helping music people find healing, hope, and stability in times of need", "donate",
        "sign up for", "the gramophone", "socials", "show more", "photo by", "photo:", "getty images"
    ]

    # Frasi "Killer": appena ne incontriamo una, consideriamo l'articolo/bio FINITO.
    cutoff_phrases = [
        "trending",
        "related articles",
        "more from grammy",
        "all grammy awards and nominations", # Taglia via l'infinita discografia delle pagine Artista!
        "latest news",
        "read more"
    ]

    for line in lines:
        l_str = line.strip()
        if not l_str:
            continue

        # Pulizia cancelletti per i check
        clean_str = re.sub(r'^[\*\-\#]+\s*', '', l_str).strip()
        lower_line = clean_str.lower()

        # --- CONTROLLO TRONCAMENTO ---
        # Se troviamo una frase killer, interrompiamo del tutto il salvataggio delle righe
        # (ma solo se abbiamo già salvato almeno 3 righe vere, per evitare falsi positivi all'inizio)
        if any(lower_line == phrase for phrase in cutoff_phrases) or lower_line.startswith("read more:"):
            if len(clean_lines) > 3:
                break # Esce dal ciclo for definitivamente. Pagina finita.

        # --- CONTROLLO SALTO RIGHE ---
        if lower_line in blacklist_exact:
            continue
        if any(lower_line.startswith(bad) for bad in ["photo by", "photo:", "getty images", "all the latest news"]):
            continue
            
        # Distrugge le tabelle markdown (utile per le discografie non intercettate)
        if l_str.startswith('|') and '|' in l_str[1:]:
            continue 

        # Se supera tutti i controlli, salva la riga
        clean_lines.append(l_str)
            
    return "\n\n".join(clean_lines)

async def parser_grammy(url: str, html_raw: str = None) -> dict:
    """
    Esegue il parsing specifico per grammy.com.
    """       
    browser_cfg = BrowserConfig(
        headless=True, 
        viewport_width=1920,
        viewport_height=1080,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        extra_args=[
            "--no-sandbox", 
            "--disable-dev-shm-usage", 
            "--disable-gpu",
            "--disable-blink-features=AutomationControlled",
            "--window-size=1920,1080"
        ]
    )
        
    # magic=True e delay garantiscono che il crawler non venga bloccato sul test dal vivo
    crawler_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        css_selector="main",
        delay_before_return_html=2.0,
        magic=True,
        excluded_tags=['nav', 'footer', 'aside', 'script', 'style', 'form', 'iframe'],
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
                raise Exception(f"Errore: {result.error_message}")

            title = result.metadata.get("title") if result.metadata else None        
            if isinstance(title, list): 
                title = title[0] if title else None

            md_text = str(result.markdown or "") 
            
            if not title or title.lower() == "grammy":
                h_match = re.search(r'^#+\s+(.*)', md_text, re.MULTILINE)
                if h_match:
                    title = h_match.group(1).strip()

            if title and isinstance(title, str):
                title = html.unescape(title)
                title = title.split('|')[0].split('—')[0].strip()
            else:
                title = "Grammy Resource"

            clean_text = clean_grammy_markdown(md_text)
            
            return {
                    "url": url, 
                    "domain": get_domain(url), 
                    "title": title,
                    "html_text": result.html, 
                    "parsed_text": clean_text
                }
    finally:
        if temp_html_path and os.path.exists(temp_html_path):
            os.remove(temp_html_path)


if __name__ == "__main__":

    test_url = "https://www.grammy.com/news/bruno-mars-2026-grammys-performance/"
   
    mio_gold_text_manuale = """
    Bruno Mars is currently nominated for three Grammy Awards at the 2026 Grammys: Record Of The Year, Song Of The Year, and Best Pop Duo/Group Performance, all for the song "APT."
    Grammy winner and current Grammy nominee Bruno Mars will perform at the 2026 Grammys.  He is nominated for three Grammy Awards this year: Record Of The Year ("APT.), Song Of The Year ("APT.") and Best Pop Duo/Group Performance ("APT.").

The full performers lineup at the 2026 Grammys includes:

Current Best New Artist Grammy nominees Addison Rae, Alex Warren, KATSEYE, Leon Thomas, Lola Young, Olivia Dean, SOMBR, and The Marías, who are performing in a special Best New Artist segment

Bruno Mars, who is currently nominated for three Grammy Awards at the 2026 Grammys

Clipse and Pharrell Williams, who are currently nominated at the 2026 Grammys for their work on the former's Let God Sort Em Out

Justin Bieber, who is currently nominated for four Grammy Awards at the 2026 Grammys

Lady Gaga, who is currently nominated for seven Grammy Awards at the 2026 Grammys

Ms. Lauryn Hill will perform in honor of D'Angelo and Roberta Flack in the annual In Memoriam tribute at the 2026 Grammys

Post Malone, Andrew Watt, Chad Smith, Duff McKagan, and Slash will perform a special tribute to Ozzy Osbourne in the annual In Memoriam segment at the 2026 Grammys

Reba McEntire joined by Brandy Clark and Lukas Nelson, who will pay tribute to those we've recently lost in the annual In Memoriam tribute at the 2026 Grammys

ROSÉ, who is currently nominated for three Grammy Awards at the 2026 Grammys

Sabrina Carpenter, who is currently nominated for six Grammy Awards at the 2026 Grammys

Tyler, The Creator, who is currently nominated for six Grammy Awards

The 2026 Grammys, hosted by Trevor Noah, will broadcast live from Crypto.com Arena in Los Angeles on Sunday, Feb. 1, at 5 p.m. PT/8 p.m. ET on the CBS Television Network and will be available to stream live and on demand on Paramount+^.

Hours ahead of the live telecast, the 2026 Grammy Awards Premiere Ceremony, where the majority of the Grammy Awards of the day are awarded, will stream live from Peacock Theater in Los Angeles on Sunday, Feb. 1, at 12:30 p.m. PT/3:30 p.m. ET on the Recording Academy's YouTube channel and on live.grammy.com.

Learn more about how to watch the 2026 Grammys.

The Grammy Awards are the only peer-recognized accolade in music and are voted on by the Recording Academy's voting membership body of music makers who represent all genres and creative disciplines, including recording artists, songwriters, producers, mixers, and engineers.

Fulwell Entertainment is producing the 2026 Grammy Awards for the Recording Academy. Ben Winston, Raj Kapoor, Jesse Collins, and Trevor Noah are executive producers.

"""
   
    filename = "grammy.com_gs.json"
   
    try:
        res = asyncio.run(parser_grammy(test_url))
        
        nuova_entry = {
            "url": res['url'],
            "domain": res['domain'],
            "title": res['title'],
            "html_text": res['html_text'], 
            "gold_text": mio_gold_text_manuale.strip()
        }

        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                try:
                    dati_esistenti = json.load(f)
                except json.JSONDecodeError:
                    dati_esistenti = []
        else:
            dati_esistenti = []

        dati_esistenti.append(nuova_entry)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(dati_esistenti, f, indent=4, ensure_ascii=False)
            
        print(f"SUCCESSO: Pagina aggiunta al file {filename}.")

    except Exception as e:
        print(f"Errore durante il test: {e}")