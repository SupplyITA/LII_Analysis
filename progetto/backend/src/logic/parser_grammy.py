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

    test_url = "https://www.grammy.com/news/2026-grammys-nominations-songwriter-of-the-year/"
   
    mio_gold_text_manuale = """
    First awarded at the 2023 GRAMMYS, Songwriter Of The Year, Non-Classical helps honor some of the most talented people behind music's biggest songs. And as this year's Category proves, there are several songwriters who have been on quite the successful run.

At the 2026 GRAMMYS, the Songwriter Of The Year, Non-Classical nominees are Amy Allen, Edgar Barrera, Jessie Jo Dillon, Tobias Jesso Jr. and Laura Veltz — all of whom are either two- or three-time nominees in the Category. 

In fact, two of them are previous winners: Allen was the first woman crowned Songwriter Of The Year, Non-Classical at the 2025 GRAMMYS, and Jesso Jr. was the inaugural recipient in 2023. 

The songwriters nominated in 2026 represent the best of songcraft across pop, country, Latin, rock, K-pop, and more. Their songs have helped turn artists like Sabrina Carpenter and Tate McCrae into the next generation of pop superstars and helped rising talents like Olivia Dean and Jessie Murph land breakout hits, guiding music into the latter half of the 2020s.

Check out the nominees for Songwriter Of The Year, Non-Classical below and read the full 2026 GRAMMYs nominations list ahead of Music's Biggest Night on Feb. 1, 2026.


Last year's winner in the Category — and first woman to win it — Amy Allen scores her third nod for Songwriter Of The Year, Non-Classical as she continues to define the sound of modern pop music.

Coming from the small town of Windham, Maine, Allen built her foundation as a songwriter at the famed Berklee College of Music before launching her career in 2018 with credits for Selena Gomez, Halsey and more. Just a few years later, Allen had earned a reputation as a go-to hit-maker for some of pop music's biggest names, and earned her first GRAMMY as a songwriter on Harry Styles' 2023 Album Of The Year winner, Harry's House.

Allen has remained a key player in pop this year, as she's continued her GRAMMY-winning partnership with Sabrina Carpenter by co-writing every track — including smash singles "Manchild" and Tears" — on the diminutive superstar's latest No. 1 album, Man's Best Friend. She's also collaborated once again with Tate McCrae on "Just Keep Watching," her high-octane contribution to F1: The Movie and its star-studded soundtrack, and reunited with Jessie Murph for slow-burning Sex Hysteria album cut "Bad As The Rest."

Allen expanded her repertoire into the world of K-pop in 2025 as well, helping JENNIE and ROSÉ score crossover hits with, respectively, the Dua Lipa duet "Handlebars" and the Bruno Mars-assisted global chart-topper "APT." She also dabbled in country music crossovers, co-penning Shaboozey and Sierra Ferrell's duet "Hail Mary," Jon Bellion's "WHY" featuring Luke Combs and "Lost In Translation," Carín León's ranchera-meets-country collab with Kacey Musgraves.

With this year's nomination, Edgar Barrera completes a well-deserved hat trick by earning nods in the Category for three consecutive years thanks to his indelible imprint on the Latin music landscape.

A Texas native who also writes under his alias Edge, Barrera's latest GRAMMY nomination for Songwriter Of The Year, Non-Classical stems from his acclaimed work with artists like KAROL G ("Milagros," from her 2025 documentary "Karol G: Tomorrow Was Beautiful"), Shakira (2024 one-off "Soltera") and Juanes ("Una Noche Contigo").

On the Regional Mexican front, Barrera also co-wrote "Me Jalo," the opener off Fuerza Regida and Grupo Frontera's collaborative EP Mala Mía as well as "Me Retiro, the latter's 2025 team-up with Santana, and also ventured into hip-hop with BIA and Young Miko's bilingual banger "BIRTHDAY BEHAVIOR." 

Notably, Barrera's work also earned him a Songwriter Of The Year nod at the 2025 Latin GRAMMYS, one of 10 nominations that remarkably also includes Producer Of The Year.

Jessie Jo Dillion joins both Allen and Barrera as a fellow three-peat nominee for Songwriter Of The Year, Non-Classical following her nominations in the Category in 2025 and 2024. 

The daughter of country songwriter Dean Dillon, Jessie Jo arrived on the Nashville scene in the early 2010s, when some of her earliest credits were writing for country icons like LeAnn Rimes ("Crazy Women") and George Strait ("The Breath You Take," co-written with her dad). 

Over the years, Dillon has become a trusted collaborator of artists like Megan Moroney and Kelsea Ballerini — continuing her hot streak with the former by adding "Bless Your Heart" to the deluxe edition of 2024's Am I Okay? and co-writing more than a dozen tracks with the latter on her fifth studio album Patterns, including the title track, singles "Sorry Mom" and "First Rodeo" and standout bonus cut "To the Men That Love Women After Heartbreak."

Dillon's success hasn't been limited to just female artists in 2025, either. She's also co-written songs for Jelly Roll ("Dreams Don't Die"), HARDY ("Bottomland") and Russell Dickerson ("Happen To Me"), as well as "Hello S—ty Day," Jake Worthington's collaboration with Miranda Lambert.

Tobias Jesso Jr. earns his second nomination for Songwriter Of The Year, Non-Classical after making history as the Category's inaugural winner back in 2023. That first year, the North Vancouver, British Columbia native's work displayed an impressive ability to write across genres, ranging from superstars like Adele, Harry Styles and Diplo to then-rising voices like Omar Apollo, Orville Peck and King Princess.

With his second nod, the GRAMMY winner continues to demonstrate that same cross-genre appeal, whether he was helping Justin Bieber craft the sound of SWAG with songs like "GO BABY," "WALKING AWAY" and lead single "DAISIES," kicking off Dijon's acclaimed sophomore album Baby with the one-two punch of "Baby!" and "Another Baby!" or collaborating with Bon Iver on SABLE fABLE deep cut "From."  

Jesso also contributed to the track list of Miley Cyrus' existential, experimental visual album Something Beautiful with a co-write on "Golden Burning Sun," aided HAIM in kicking off their fourth album with lead single "Relationships" and helped Olivia Dean earn her well-deserved breakout moment with the inescapable hit "Man I Need," which just cracked the Top 5 of the Billboard Hot 100 as of press time.


Laura Veltz was also one of the first songwriters to ever land a nod for Songwriter Of The Year, Non-Classical back in 2023, and now she's back with her second nomination in the Category.

Prior to her songwriting career, though, Veltz sang with her family band, Cecilia, who released just a single album (2006's This) under the name The Veltz Family. After relocating to Nashville in 2008, the former frontwoman began working full-time as a songwriter with credits for country acts like Edens Edge, Jana Kramer, Chris Young, and Eli Young Band throughout the early 2010s. 

Cut to 2025 and Veltz continues to push the boundaries of modern country by working with Maren Morris ("Grand Bouquet"), BigXthaPlug and Tucker Wetmore ("About You") and Josh Ross ("Leave Me Too"). She also co-penned multiple tracks off Jessie Murph's sophomore album, including breakout single "Blue Strips," "Touch Me Like a Gangster" and the Bailey Zimmerman-assisted "Someone In This Room," and reunited with Demi Lovato to write "You'll Be OK, Kid," the theme from the pop star's 2024 documentary "Child Star."




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