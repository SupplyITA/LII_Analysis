import os
import tempfile
from urllib.parse import urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
import json, asyncio
import re

def get_domain(url: str) -> str:
    """ Restituisce il dominio in minuscolo da un URL dato """
    parsed = urlparse(url)
    return parsed.netloc.lower()

async def parser_wikipedia(url: str, html_raw: str = None) -> dict:
    """
    Esegue il parsing specifico per wikipedia.
    Acquisizione sia tramite URL sia tramite HTML locale (se presente)
    """
    
    browser_cfg = BrowserConfig(headless=True, extra_args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
    
    # rimuove elementi non informativi 
    js_script = """
    let pageTitle = "No Title Found";
    let heading = document.getElementById('firstHeading');
    if (heading) {
        pageTitle = heading.innerText;
    } else if (document.title) {
        pageTitle = document.title.replace(' - Wikipedia', '');
    }

    document.querySelectorAll('sup, nav, footer, script, style, .infobox, .reflist, .navbox, .mw-editsection, .reference, .metadata, .printfooter').forEach(el => el.remove());
    let seeAlso = document.getElementById('See_also');
    if (seeAlso && seeAlso.parentNode) {
        while (seeAlso.parentNode.nextSibling) { seeAlso.parentNode.nextSibling.remove(); }
        seeAlso.parentNode.remove();
    }

    let content = document.querySelector('#mw-content-text');
    if (content) {
        content.setAttribute('data-wiki-title', pageTitle.replace(/"/g, '&quot;'));
    }
    """
    # configurazione del crawler
    crawler_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, css_selector="#mw-content-text", js_code=js_script)

    # gestione del parsing di HTML diretto
    target_url = url
    temp_html_path = None
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
            title = "No Title Found"
            if result.html:
                # Estrae l'attributo che abbiamo iniettato tramite JavaScript
                match = re.search(r'data-wiki-title="([^"]+)"', result.html)
                if match:
                    title = match.group(1).replace('&quot;', '"')
                    
            # Fallback di sicurezza nel caso in cui stia usando il comportamento base
            if title == "No Title Found" and result.metadata:
                title = result.metadata.get("title", "No Title Found")
            
            return {
                "url": url,
                "domain": get_domain(url),
                "title": title,
                "html_text": result.html,
                "parsed_text": result.markdown or ""
            }
    finally:
        if temp_html_path and os.path.exists(temp_html_path):
            os.remove(temp_html_path)


# -------------------------- AGGIUNTA URLLLLLLLLLLLL --------------------------
if __name__ == "__main__":

    test_url = "https://en.wikipedia.org/wiki/Sapienza_University_of_Rome" 
   
    mio_gold_text_manuale = """
For other universities of Rome, see University of Rome (disambiguation).
"Sapienza" redirects here. For other uses, see Sapienza (disambiguation).The Sapienza University of Rome[7] (Italian: Università degli Studi di Roma "La Sapienza"), also known as La Sapienza (The Wisdom), is a public research university located in Rome, Italy.[8] It was founded in 1303 and is one of the world's oldest universities.[9] With over 110,000 students, it is also the largest university in Europe.[10] Due to its size, funding, and numerous laboratories and libraries, Sapienza is a global major education and research centre.[11][12] The university is located mainly in the Città Universitaria (University city), which covers 44 ha (110 acres) near the Campo Verano cemetery, with different campuses, libraries and laboratories in various locations in Rome.

Sapienza was founded on 20 April 1303 by decree from Pope Boniface VIII as a Studium for ecclesiastical studies under more control than the free-standing universities of Bologna and Padua. In 1431 Pope Eugene IV completely reorganized the studium and decreed that the university should expand to include the four schools of Law, Medicine, Philosophy, in addition to the existing Theology. In the 1650s the university became known as Sapienza, meaning "wisdom" or "knowledge", a title it still retains.[13] After the capture of Rome by the forces of the Kingdom of Italy in 1870, La Sapienza rapidly expanded as the chosen main university of the capital of the newly unified state. In 1935 the new university campus, planned by Marcello Piacentini, was completed.[14]

Sapienza teaches and conducts research in all pure and applied sciences and humanities. Sapienza houses 50 libraries with over 2.7 million books, most notably the Alessandrina University Library, built in 1667 by Pope Alexander VII, housing 1.5 million volumes.[15] In addition it has 19 museums, a botanical garden, and three university hospitals.[16] Sapienza's alumni includes 10 Nobel laureates, Italian prime ministers, one pope, presidents of the European Parliament and European Commissioners, as well as several notable religious figures, supreme court judges, and astronauts.[17]

History
The Sapienza University of Rome was founded in 1303 with the papal bull In Supremae praeminentia Dignitatis, issued on 20 April 1303 by Pope Boniface VIII, as a Studium for ecclesiastical studies more under his control than the universities of Bologna and Padua,[18] making it the first pontifical university.[14]

In 1431 Pope Eugene IV completely reorganized the studium with the bull In supremae, in which he granted masters and students alike the broadest possible privileges and decreed that the university should include the four schools of Law, Medicine, Philosophy and Theology. He introduced a new tax on wine to raise funds for the university; the money was used to buy a palace which later housed the Sant'Ivo alla Sapienza church.

However, the university's days of splendour came to an end during the sack of Rome in 1527, when the studium was closed, some of the professors were killed and others dispersed.[19] Pope Paul III restored the university shortly after his election to the pontificate in 1534.

In the 1650s the university became known as Sapienza, meaning wisdom, a title it retains. In 1703, with his private funds, Pope Clement XI purchased some land on the Janiculum, where he created a botanical garden, which soon became the most celebrated in Europe through the labours of the Trionfetti brothers. The first complete history of the Sapienza University was written in 1803–1806 by Filippo Maria Renazzi.[20]

University students were newly animated during the 19th-century Italian revival. In 1870, La Sapienza stopped being the papal university and became the university of the capital of Italy. In 1935 the new university campus, planned by Marcello Piacentini, was completed.

On 15 January 2008 the Vatican cancelled a planned visit to La Sapienza University by Pope Benedict XVI who was to speak at the university ceremony launching the 2008 academic year[21] due to protests by some students and professors.[22] The title of the speech would have been 'The Truth Makes Us Good and Goodness is Truth'.[23] Some students and professors protested in reaction to a 1990 speech that Pope Benedict XVI (then Cardinal Joseph Ratzinger) gave in which he, in their opinion, endorsed the actions of the church against Galileo in 1633.[14][21]
Campuses
Sapienza University has many campuses in Rome, but its main campus is the Città Universitaria (University city), which covers 44 ha (110 acres) near the Roma Tiburtina Station. The university has satellite campuses outside Rome, the main one of which is in Latina.

In 2011 a project was launched to build a campus with residence halls near Pietralata station, in collaboration with the Lazio region.[24] To cope with the ever-increasing number of applicants, the Rector also approved a new plan to expand the Città Universitaria, reallocate offices and enlarge faculties, as well as create new campuses for hosting local and foreign students.

The Alessandrina University Library[25] (Biblioteca Universitaria Alessandrina), built in 1667 by Pope Alexander VII, is the main library housing 1.5 million volumes; it has some important collections including collezione ciceroniana and Fondo Festa.

Points of interest
Orto Botanico dell'Università di Roma "La Sapienza", a botanical garden
Sant'Ivo alla Sapienza
San Pietro in Vincoli: the cloister is part of the Engineering School
Villa Mirafiori: a Neo-Renaissance palace built during the 19th century, some rooms are decorated with fine frescoes. The Department of Philosophy is located in this building.
Centro MedioEvA
Sapienza University of Rome is one of the three institutions that, in 2022, contributed to the founding of the Centro MedioEvA. Founded by Donatella Manzoli (Sapienza University) and Elisabetta Bartoli (University of Siena), the Centre brings together a group of specialists in medieval literatures from the University of Siena, Sapienza University, and the University of Tours. This entirely new cultural initiative aims to promote, coordinate, and carry out research activities, projects, printed publications, and digital resources on literature composed in Latin and in the vernacular languages by women during the medieval millennium (6th–15th centuries).

Adopting a multidisciplinary and comparative approach, MedioEvA seeks to investigate women's literatures and the cultural role of women within the medieval world, challenging deeply rooted yet anachronistic stereotypes. MedioEvA also aims to explore both the objective and subjective perceptions of women across the centuries of the Middle Ages, and—through the tools of philological and literary criticism—it fosters studies, critical editions, editions of unpublished works, and translations of texts that have either never been translated or are in need of new renderings.

MedioEvA also aspires to serve as a key platform for disseminating and promoting this little-known body of literature beyond the narrow circle of specialists, acting as a promoter of initiatives that seek to convey an updated understanding of the cultural role of medieval women and of the Middle Ages as a whole (such as student outreach, teacher training, and participation in cultural festivals). Knowledge of women's literatures will enrich the contours of the Middle Ages, which forms the recognised foundation of our present.[26]

Among the scholarly works supported by the Centro MedioEvA, two notable examples are the volumes Scrittrici del Medioevo. Un'antologia[27] and Genere e generi. Scritture di donne nell'Europa medievale.[28]

Academics
Since the 2011 reform, Sapienza University of Rome has eleven faculties and 65 departments. Today Sapienza, with 140,000 students and 8,000 among academic and technical and administrative staff, is the largest university in Italy. The university has significant research programmes in the fields of engineering, natural sciences, biomedical sciences and humanities. It offers 10 Masters Programmes taught entirely in English.[citation needed]

Ranking
University rankings
Global – Overall
ARWU World[29]	151–200 (2020)
CWUR World[30]	113 (2021–2022)
CWTS World[31]	81 (2020)
QS World[32]	128 (2026)
THE World[33]	197 (2022)
USNWR Global[34]	=114 (2021)
In 2025, Sapienza ranked 1st among universities in Italy and Southern Europe in the Academic Ranking of World Universities (ARWU)[35][36] and according to CWUR.

As of the 2016 Academic Ranking of World Universities (ARWU), Sapienza is positioned within the 151–200 group of universities and among the top 3% of universities in the world.[37][38]

In 2016, the Center for World University Rankings ranked the Sapienza University of Rome as the 90th in the world and the top in Italy in its World University Rankings.[39]

According to the QS Graduate Employability Ranking 2020, Sapienza places first amongst Italian universities in Alumni Outcomes thanks to the number of university graduates employed in large companies and in managerial positions.[40]

In 2024, Sapienza University of Rome ranked 134th in the world in QS World University Rankings.[41] Sapienza is ranked 1st in the world by QS World University Rankings in the subject of Classics and Ancient History.[42] In the same ranking, Sapienza ranks 10th in the subject Archaeology.[43] Sapienza is ranked 36th in the subject Physics & Astronomy,[44] 39th in Arts and Humanities[45] ,70th in Psychology[46] and 72th in Medicine.[47]

Admission
To cope with the large demand for admission to the university courses, some faculties hold a series of entrance examinations. The entrance test often decides which candidates will have access to the undergraduate course. For some faculties, the entrance test is only a means through which the administration acknowledges the students' level of preparation. Students that do not pass the test can still enroll in their chosen degree courses but have to pass an additional exam during their first year.[citation needed]

Publications
Archaeology
Vicino Oriente (lit. 'Near East') journal
Notable people
Some of the notable alumni and professors
Picture	Alumni and professors	Academic degree	Note	Awards
	Maria Montessori	Natural sciences	Founder of the Montessori method of education, regarded to be one of the most influential female physicians	
	Federico Fellini	Law	One of the most important filmmakers of the 20th century	Academy Honorary Award, European Film Awards
	Evangelista Torricelli	Physics	Inventor of the barometer. He made significant contributions in optics and on the method of indivisibles.	
	Enrico Fermi	Physics	Physicist, colleague and close friend of Ettore Majorana. A key figure in the creation of the atomic bomb, he discovered: new radioactive elements produced by neutron irradiation, controlled nuclear chain reaction. He is also known for the Fermi–Dirac statistics and the theory of beta decay	Nobel Prize in Physics (1938)[48]
	Emilio Gino Segrè	Physics	Physicist, colleague and close friend of Ettore Majorana. A key figure in the creation of the atomic bomb, he helped discover the antiproton and the elements astatine, and technetium	Nobel Prize in Physics (1959)
	Daniel Bovet	Psychobiology	Nobel Prize in Physiology or Medicine (1957) for his discovery of drugs that block the actions of specific neurotransmitters. He is best known for his discovery in 1937 of antihistamines, which block the neurotransmitter histamine and are used in allergy medication	Nobel Prize in Physiology or Medicine (1957)
Ennio De Giorgi	Mathematics	Mathematician, who worked on partial differential equations. He solved Bernstein's problem about minimal surfaces. He solved Hilbert's nineteenth problem on the regularity of solutions of elliptic partial differential equation.	Caccioppoli Prize (1960), Wolf Prize (1990)
	Umberto Guidoni	Astrophysics	European Space Agency and Italian Space Agency astronaut (ESA/ASI) and a veteran of two NASA Space Shuttle missions	
	Mario Draghi	Economics	Prime Minister of Italy (2021–2022). President of the European Central Bank. Governor for Italy on the Boards of Governors of the International Bank for Reconstruction and Development and the Asian Development Bank. Ex governor of the Bank of Italy. Ex Italian Executive Director at the World Bank. Ex director general of the Italian Treasury. Ex vice chairman and managing director of Goldman Sachs International	
	Sergio Balanzino	Law	Deputy Secretary General of NATO. Two times NATO General Secretary	
	Antonio Tajani	Law	President of the European Parliament. Former European Commissioner for Industry and Entrepreneurship	
	Federica Mogherini	Political Science	High Representative of the Union for Foreign Affairs and Security Policy and Rector of the College of Europe.	
	Sergio Mattarella	Law	12th President of Italy	
	Vito Volterra	Mathematical physics	Mathematician and physicist, known for the theory of integral equations and the Lotka–Volterra equations	
	Gabriele d'Annunzio	Literature	Poet, journalist, playwright, soldier, politician. He was part of the literary movement called the Decadent movement.	
	Bernardo Bertolucci	Modern literature	Film director and screenwriter, whose films include The Conformist, Last Tango in Paris, 1900, The Last Emperor, The Sheltering Sky and The Dreamers	2 Nastro d'Argento Best Director, Academy Award for Best Director, Academy Award for Best Adapted Screenplay, Golden Globe Award for Best Director, Golden Globe Award for Best Screenplay, David di Donatello for Best Director, David di Donatello for Best Script, Golden Lion for his career at the Venice Film Festival, Honorary Palme d'Or at Cannes Film Festival
	Charles Ponzi	Business (not completed)	Known for the fraudulent business scheme named after him, the Ponzi scheme	
	Enrico Giovannini	Economics, Statistics	Italian Minister of Labor and Social Policies, President of the Italian Statistical Institute (Istat). Chief Statistician and Director of the Statistics Directorate of the Organisation for Economic Co-operation and Development (OECD) in Paris. Professor of Economic Statistics.	
Abdirashid Ali Shermarke	Political Science	first Prime Minister of Somalia and second President of Somalia	
	Luca Cordero di Montezemolo	Accounting	Chairman of Ferrari, president of Confindustria, president of Nuovo Trasporto Viaggiatori (NTV). He was also the Chairman of Fiat S.p.A. from 2004 to 2010.	
	Ignazio Visco	Economics	Governor of the Banca d'Italia (Bank of Italy)	
	Massimiliano Fuksas	Architecture	Architect	Grand Prix d'Architecture Française (1999), Commandeur de l'Ordre des Arts et des Lettres de la République Française (2000), Honorary Fellowship of the American Institute of Architects (2002), Honorary Fellowship of the Royal Institute of British Architects (2006)
	Carlo Verdone	Modern literature	Prominent actor, screenwriter and film director.	
	Paolo Gentiloni	Political Science	European Commissioner in the Von der Leyen Commission since September 2019 and former Italian Prime Minister from December 2016 to June 2018	
Giorgio Gaja	Law	Elected in 2011 as a judge of the International Court of Justice	
	Pier Carlo Padoan	Economics	Deputy Secretary General at the OECD in Paris, and their chief economist. OECD 's G20 Finance Deputy, leads the initiatives 'Strategic Response', 'Green Growth' and 'Innovation'. Italy's finance minister	
	Giuseppe Conte	Politics	Former Prime Minister of Italy and leader of the Five Star Movement	
	Giorgio Parisi	Physics	Winner of the 2021 Nobel Prize in Physics. Also attended Sapienza as a student.	Nobel Prize in Physics (2021), Dirac Medal (1999), and others.
	Andrea Zitolo	Physical-Chemist	SOLEIL Synchrotron Principal Scientist & Knight of the Ordre des Palmes Académiques	
Selection of Alumni
Sapienza University can boast several illustrious professors and alumni from the past and the present. From Nicolaus Copernicus to Maria Montessori, from Luigi Pirandello to Tullio De Mauro, from Sergio Mattarella to Mario Draghi. Numerous Nobel Prize winners have been professors or have graduated from Sapienza: Guglielmo Marconi, Enrico Fermi, Daniel Bovet, Emilio Segrè, Giulio Natta, Carlo Rubbia, Franco Modigliani.

Nobel Prize Winners
Guglielmo Marconi – 1909 Nobel Prize in Physics; taught Electro-magnetic Waves - Physics at Sapienza 1935–1937.
Enrico Fermi – 1938 Nobel Prize in Physics; Chair of Theoretical Physics at Sapienza 1926–1938.
Daniel Bovet – 1957 Nobel Prize in Medicine and Physiology, Chair of Psychobiology at Sapienza 1971–1982.
Emilio Segrè – 1959 Nobel Prize in Physics; Chair of Physics at Sapienza 1928–1935.
Giulio Natta – 1963 Nobel Prize in Chemistry; Chair of Physical Chemistry at Sapienza 1935–1937.
Carlo Rubbia – 1984 Nobel Prize in Physics; Assistant Professor of Physics 1959–1960.
Franco Modigliani – 1985 Nobel Prize in Economics; graduated in Law in 1939.
Barry C. Barish – 2017 Nobel Prize in Physics; Fermi Chair of Physics at Sapienza 2019.
Giorgio Parisi – 2021 Nobel Prize in Physics; Chair of Theoretical Physics 1992–2018.
Serge Haroche – 2012 Nobel Prize in Physics; Fermi Chair of Physics at Sapienza 2022.
Politics, Diplomats & Administrators
Giulio Andreotti (1919–2013), politician.
Laura Boldrini, politician.
Giuseppe Conte, politician.
Francesco del Bene, law firm founder.
Mario Draghi, economist, politician.
Paolo Gentiloni, politician.
Gianni Letta, politician and journalist.
Sergio Mattarella, politician, 12th President of Italy.
Firmin Edouard Matoko, Congolese diplomat and Assistant Director-General for Priority Africa and External Relations at UNESCO.
Federica Mogherini, politician and rector of the College of Europe.
Antonio Rodotà, European Space Agency Director General.
Francesco Rutelli, politician.
Antonio Tajani, politician.
Chrysoula Zacharopoulou, French Minister.
Journalism
Paolo Mieli, journalist.
Economics
Mario Draghi, economist, politician.
Ignazio Visco, economist.
Enrico Giovannini, statistician.
Literature and Arts
Barbara Jatta, historian of art.
Alberto Angela, paleontologist.
Emma Castelnuovo (1913–2014), mathematician.
Porpora Marcasciano, sociologist and LGBT activist.
Business
Luca Montezemolo, entrepreneur and Ferrari's CEO
Pierpaolo Piccioli, Valentino and Balenciaga creative director
Entertainment
Luca Guadagnino, director.
Antonello Venditti, singer-songwriter.
Carlo Verdone, actor, director.
Claudio Baglioni, musician.
Edoardo Leo, actor.
Cristiana Capotondi, actor.
Science and Academia
Evangelina Bottero (1859–1950), teacher and populariser of science.
Maria Montessori (1870–1952), physician and pedagogue.
Eugenio Pacelli (1876–1958), Pope.
Cesare Bazzani (1873–1939), architect.
María Casanova de Chaudet (1899–1947), director of Argentina's first petrographic laboratory.
Barbara Jatta, historian of art.
Alberto Angela, paleontologist.
Sports
Caterina Banti, sailor, Olympic champion.[49]
Andrea Stella, Formula One engineer and executive.
Faculty and staff
Among the prominent scholars who have taught at the Sapienza University of Rome are architects Ernesto Basile and Bruno Zevi; chemist Emanuele Paternò; jurists Antonio Salandra, Sabino Cassese and Giuliano Amato; mathematician Vito Volterra; pharmacologist and Nobel Laureate in Physiology or Medicine Daniel Bovet; chemist and Nobel Laureate Giulio Natta; philosophers Luigi Ferri and Augusto Del Noce; physicist and Nobel Laureate in Physics Enrico Fermi; political scientist Roberto Forges Davanzati.

Carlo Costamagna
Cardinal Mazarin
Mario Oriani-Ambrosini
Corrado Gini, statistician
Lucio Bini and Ugo Cerletti, psychiatrists
Corrado Böhm, computer scientist
Benedetto Castelli, mathematician
Andrea Cesalpino, physician and botanist
Federigo Enriques, mathematician
Maria Montessori, physician and pedagogist
Paola S. Timiras, biologist
Barnaba Tortolini, mathematician
Andrea Zitolo, physical-chemist
Edoardo Amaldi
Oscar D'Agostino
Ettore Majorana
Bruno Pontecorvo
Franco Rasetti
Giovanni Battista Beccaria
Giovanni Jona-Lasinio
Luciano Maiani
Domenico Pacini
Antonio Signorini
Nicola Cabibbo, President of the Pontifical Academy of Sciences
Cora Sternberg
Carlo Franzinetti, physicist
Alessandro Piccolo (agricultural scientist), Professor at University of Naples Federico II, Humboldt Prize in Chemistry
Salvatore Dierna, architect, professor of environmental design[50]
Humanities
Anna Maria Bisi, archaeologist
Cesare Borgia, Cardinal, condottiero and politician of the 15th century
Piero Boitani, literary critic, writer and academic
Giovanni Vincenzo Gravina, jurisconsult
Silvia Berti, historian
Lazarus Buonamici, renaissance humanist
Umberto Cassuto, Hebrew language and Bible scholar
Marcel Danesi, language scientist
Ernesto de Martino, anthropologist and ethnologist
Carlo Innocenzio Maria Frugoni, poet
Count Angelo de Gubernatis, orientalist
Predrag Matvejević, writer and academic
Santo Mazzarino, leading historian of ancient Rome and ancient Greece
Giuseppe Tucci, orientalist
Mario Liverani, orientalist
Paolo Matthiae, director of the archeological expedition of Ebla
Antonio Nibby, archaeologist
Diego Laynez, second general of the Society of Jesus
Giulio Mazzarino, politician and cardinal
Mauro Olivieri, professor of electronics
Alessandro Roncaglia, economist
Giulio Salvadori, literary critic and poet
Giuseppe Scaraffia, literary critic
Ugo Spirito, philosopher
Giuseppe Ungaretti, poet
Bernardino Varisco, philosopher
Musine Kokalari, Albanian writer
"""
   
    filename = "progetto/gs_data/en.wikipedia.org_gs.json"
   
    try:
        res = asyncio.run(parser_wikipedia(test_url))
        
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
            
