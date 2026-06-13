import json, os, re, html
from urllib.parse import urlparse
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Depends
from typing import List, Dict, Optional
import mistune
from bs4 import BeautifulSoup
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database import get_db
from src.models import WebResource, GoldStandard
from src.init_db import init_db

from src.logic.metrics import compute_token_level_eval
from src.logic.gs_manager import load_domains 
from src.logic.parser_wikipedia import parser_wikipedia
from src.logic.parser_grammy import parser_grammy
from src.logic.parser_huddle import parser_huddle
from src.logic.parser_academia import parser_academia

# --------------- gestione avvio server (lifespan) ---------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """ Esegue operazioni di inizializzazione all'avvio del server """
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

# --------------- schemi pydantic ---------------
class ParseResponse(BaseModel):
    """ Schema di risposta per l'operazione di parsing """
    url: str
    domain: str
    title: str
    html_text: str
    parsed_text: str

class ParseRequest(BaseModel): # al posto di parsehtmlrequest !!!!!
    """ Input per POST/parse """
    url: str
    html_text: Optional[str] = None # invio manuale HTML
    local: Optional[bool] = False   # se true usa il DB

class TokenLevelEval(BaseModel):
    """ Metriche per la valutazione """
    precision: float
    recall: float
    f1: float
    
class EvaluationResponse(BaseModel):
    """ Schema di risposta finale per la valutazione """
    token_level_eval: TokenLevelEval
    judge_score: Optional[float] = None
    x_eval: Optional[Dict] = {} 

class EvaluateRequest(BaseModel):
    """ Input richiesto per endpoint di valutazione """
    parsed_text : str
    gold_text: str
    
class JudgeResponse(BaseModel):
    model_name: str
    judge_score: int
    judge_feedback: str

# ---------------------------- Funzioni di supporto ----------------------------
def remove_markdown(md: str) -> str:
    """  Rimuove il Markdown da una stringa, restituendo solo il testo pulito """
    if not md: return ""

    html_str = mistune.html(md)
    soup = BeautifulSoup(html_str, "html.parser")
    
    for tag in soup.find_all(True):
        tag.unwrap()
    text = html.unescape(str(soup))
    text = re.sub(r'[ \t]+', ' ', text) 
    text = re.sub(r'\n+', '\n', text) 
    return text.strip()

async def get_parsed_data(url: str, html_text: str = None):
    """
    Seleziona la funzione di parsing specifica per ogni URL in base al dominio.
    Se html_text è fornito, il parsing avviene localmente
    """    
    netloc = urlparse(url).netloc.lower()
    
    if "wikipedia.org" in netloc:
        return await parser_wikipedia(url, html_raw=html_text)
    elif "huddle.org" in netloc:
        return await parser_huddle(url, html_raw=html_text)
    elif "grammy.com" in netloc:
        return await parser_grammy(url, html_raw=html_text)
    elif "academia.edu" in netloc:
        return await parser_academia(url, html_raw=html_text)
    
    return None

# ---------------------------- Endpoint ----------------------------

@app.get("/domains")
def get_domains():
    """ Restituisce la lista dei domini supportati """
    return {"domains": load_domains()}

''' non serve più !!!!!!!!!!!!! vuole solo post credo
@app.get("/parse", response_model=ParseResponse)
async def parse(url: str, db: Session = Depends(get_db)):
    """ Scarica un URL, lo parsa e lo SALVA NEL DATABASE """
    supported_domains = load_domains()
    if not any(d in url for d in supported_domains):
        raise HTTPException(status_code=400, detail="Dominio non supportato")

    try:
        result = await get_parsed_data(url)
        if not result:
            raise HTTPException(status_code=400, detail="Parser specifico non trovato")
        
        #salviamo l'HTML e i metadati nel database se non esistono già
        existing = db.query(WebResource).filter(WebResource.url == url).first()
        if not existing:
            nuova_risorsa = WebResource(
                url=result["url"],
                domain=result["domain"],
                title=result["title"],
                html_text=result["html_text"]
            )
            db.add(nuova_risorsa)
            db.commit()

        return result
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"URL irraggiungibile o errore: {str(e)}")
'''

@app.post("/parse", response_model=ParseResponse)
async def parse(request: ParseRequest, db: Session = Depends(get_db)):    
    """ Esegue il parser su un testo HTML fornito e lo SALVA NEL DATABASE """
    # verifica se il dominio è supportato
    supported_domains = load_domains()
    if not any(d in request.url for d in supported_domains):
        raise HTTPException(status_code=400, detail="Dominio non supportato")

    # gestione modalità local
    html_to_use = request.html_text
    
    if request.local:
        db_res = db.query(WebResource).filter(WebResource.url == request.url).first()
        if not db_res:
            raise HTTPException(status_code=404, detail="URL non presente nel database, impossibile parsing locale")
        html_to_use = db_res.html_text

    # parsing
    try:
        result = await get_parsed_data(request.url, html_text=html_to_use)
        if not result:
            raise HTTPException(status_code=400, detail="Parser specifico non trovato")
        
        # salvataggio se risorsa nuova e non locale
        if not request.local:
            existing = db.query(WebResource).filter(WebResource.url == request.url).first()    
            if not existing:
                nuova_risorsa = WebResource(
                url=result["url"],
                domain=result["domain"],
                title=result["title"],
                html_text=result["html_text"]
                )
                db.add(nuova_risorsa)
                db.commit()
        return result                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore di parsing HTML: {str(e)}")

@app.get("/gold_standard")
def get_gold_standard(url: str, db: Session = Depends(get_db)): 
    """ Interroga il DATABASE per ottenere il gold standard di un url """
    gs_entry = db.query(GoldStandard).filter(GoldStandard.url == url).first()
    if not gs_entry:
        raise HTTPException(status_code=404, detail="URL non trovato nel Database GS")
    
    return {
        "url": gs_entry.url,
        "domain": gs_entry.web_resource.domain if gs_entry.web_resource else "Sconosciuto",
        "gold_text": gs_entry.gold_text
    }

@app.get("/gold_standard_urls")
def get_gold_standard_urls(domain:str, db: Session = Depends(get_db)):
    """ Restituisce la lista di tutti gli URL presenti nel GS per un dominio """

    # join tra gs e webresource per filtrare un dominio
    urls = db.query(GoldStandard.url).join(WebResource).filter(WebResource.domain == domain).all()
    if not urls:
        raise HTTPException(status_code=404, detail="Dominio non supportato o GS mancante nel Database")

    urls_list = [u[0] for u in urls]
    return {"gold_standard_urls": urls_list}

@app.post("/evaluate", response_model=EvaluationResponse)
def evaluate(request: EvaluateRequest):
    """ Confronta un testo parsato con il gold standard e restituisce le metriche di valutazione  """
    clean_parsed_text = remove_markdown(request.parsed_text)
    metrics = compute_token_level_eval(clean_parsed_text, request.gold_text)
    return {"token_level_eval": metrics}


@app.get("/full_gs_eval", response_model=EvaluationResponse)
async def full_gs_eval(domain: str, db: Session = Depends(get_db)):
    """ Valutazione complessiva leggendo dal DATABASE """
    gs_entries = db.query(GoldStandard).join(WebResource).filter(WebResource.domain == domain).all()
    
    if not gs_entries:
        raise HTTPException(status_code=404, detail="Dominio non trovato nel DB")
    
    results = []
    for entry in gs_entries:
        try:
            parsed_data = await get_parsed_data(entry.url, html_text=entry.web_resource.html_text)
            if parsed_data:
                raw_md = parsed_data.get("parsed_text", "")
                clean_parsed_text = remove_markdown(raw_md)
                metrics = compute_token_level_eval(clean_parsed_text, entry.gold_text)
                results.append(metrics)
        except Exception as e:
            print(f"Errore su {entry.url}: {str(e)}")
            continue

    if not results:
        raise HTTPException(status_code=500, detail="Impossibile valutare il dominio") 
    
    # calcolo delle metriche aggregate
    avg_precision = sum(r["precision"]  for r in results) / len(results)
    avg_recall = sum(r["recall"] for r in results) / len(results)
    avg_f1 = sum(r["f1"] for r in results) / len(results)

    return {
        "token_level_eval": {
            "precision": round(avg_precision, 4),
            "recall": round(avg_recall, 4),
            "f1": round(avg_f1, 4)
        }
    }

@app.post("/evaluate_judge", response_model=JudgeResponse)
async def evaluate_judge(request: EvaluateRequest):
    """ Invia il testo a Ollama per una valutazione """
    pass

@app.get("/db_stats")
def get_db_stats(db: Session = Depends(get_db)):
    """ Restituisce conteggi per dominio """

    # conta quante pagine ci sono per ogni dominio
    stats = db.query(WebResource.domain, func.count(WebResource.url)).group_by(WebResource.domain).all()
    domain_counts = {d: c for d, c in stats} # dizionario del tipo { dominio: conteggio pagine }

    return {
        "web_resources": domain_counts,
        "gold_standard": domain_counts,
        "avg_eval": {},     # medie voti
        "avg_eval_judge": {}    # medie voti dati da Ollama
    }

@app.get("/db_schema")
def get_db_schema():
    """ Restituisce la decsrizione tecnica delle tabelle """
    return {
        "web_resources": {
            "url": "varchar(2048), PK",
            "domain": "varchar(255)",
            "title": "varchar(2048)",
            "html_text": "longtext",
            "created_at": "datetime"
        },
        "gold_standard": {
            "url": "varchar(2048), PK, FK(web_resources.url)",
            "gold_text": "longtext",
            "created_at": "datetime"
        }
    }

@app.get("/status")
def get_status(db: Session = Depends(get_db)):
    """ Verifica stato di backend, DB e Ollama """

    status = {
        "backend": "ok",
        "database": "ok",
        "ollama": "ok",        
    }

    # controllo db
    try:
        db.execute("SELECT 1")  
    except:
        status["database"] = "error"

    # controllo ollama
    # da completare !!!

    return status

@app.post("/add_web_resource")
def add_web_resource(request: ParseRequest, db: Session = Depends(get_db)):
    """ Aggiunge una risorsa web nella tabella web_resources con l'HTML fornito in input """

    # controlla se esiste già
    existing = db.query(WebResource).filter(WebResource.url == request.url).first()
    if existing:
        return {
            "status": "error",
            "message": "URL già presente"
        }
    
    nuova = WebResource(
        url = request.url,
        domain = urlparse(request.url).netloc.lower(),
        title = "Inserito manualmente",
        html_text = request.html_text
    )
    db.add(nuova)
    db.commit()
    return { "status": "ok" }

@app.post("/add_gold_standard")
def add_gold_standard(request: EvaluateRequest, url: str, db: Session = Depends(get_db)):
    """Aggiunge un'entry nella tabella gold_standard """
    res = db.query(WebResource).filter(WebResource.url == url).first()
    if not res:
        raise HTTPException(status_code = 400, detail = "URL non presente in web_resources")
    
    # se esiste il gs va aggiornato, altrimenti va creato
    existing_gs = db.query(GoldStandard).filter(GoldStandard.url == url).first()
    if existing_gs:
        existing_gs.gold_text = request.gold_text
    else:
        db.add(GoldStandard(url=url, gold_text=request.gold_text))
    
    db.commit()
    return { "status": "ok" }

@app.delete("/delete_web_resource")
def delete_web_resource(url: str, db: Session = Depends(get_db)):
    """ Rimuove una risorsa web dalla tabella web_resources e a cascata con FK, il gold_standard associato """

@app.delete("/delete_gold_standard")
def delete_gold_standard(url: str, db: Session = Depends(get_db)):
    """ Rimuove solo l'entry dalla tabella gold_standard, lasciando intatta la web_resource associata """