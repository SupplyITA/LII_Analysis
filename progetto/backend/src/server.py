import json
import os
import re
from urllib.parse import urlparse
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Depends
from typing import List, Dict, Optional
import mistune
import html
from bs4 import BeautifulSoup
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from src.database import get_db
from src.models import WebResource, GoldStandard
from src.init_db import init_db

from src.logic.metrics import compute_token_level_eval
from src.logic.gs_manager import load_domains 
from src.logic.parser_wikipedia import parser_wikipedia
from src.logic.parser_grammy import parser_grammy
from src.logic.parser_huddle import parser_huddle
from src.logic.parser_academia import parser_academia

# ---------------gestione avvio server(lifespan) ---------------
@asynccontextmanager
async def lifespan(app: FastAPI):
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

class TokenLevelEval(BaseModel):
    """ Metriche per la valutazione """
    precision: float
    recall: float
    f1: float
    
class EvaluationResponse(BaseModel):
    """ Schema di risposta finale per la valutazione """
    token_level_eval: TokenLevelEval
    x_eval: Optional[Dict] = {} 

class EvaluateRequest(BaseModel):
    """ Input richiesto per endpoint di valutazione """
    parsed_text : str
    gold_text: str

class ParseHtmlRequest(BaseModel):
    """ Richiesta per parsing da HTML diretto """
    url: str
    html_text: str

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
    
@app.post("/parse", response_model=ParseResponse)
async def parse_post(request: ParseHtmlRequest, db: Session = Depends(get_db)):
    """ Esegue il parser su un testo HTML fornito e lo SALVA NEL DATABASE """
    supported_domains = load_domains()
    if not any(d in request.url for d in supported_domains):
        raise HTTPException(status_code=400, detail="Dominio non supportato")
    try:
        result = await get_parsed_data(request.url, html_text=request.html_text)
        if not result:
            raise HTTPException(status_code=400, detail="Parser specifico non trovato")
        
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

@app.get("/full_gold_standard")
def get_full_gold_standard(domain: str, db: Session = Depends(get_db)):
    """ Interroga il DATABASE per la lista degli elementi GS di un dominio """
    gs_entries = db.query(GoldStandard).join(WebResource).filter(WebResource.domain == domain).all()
    
    if not gs_entries:
        raise HTTPException(status_code=404, detail="Dominio non supportato o GS mancante nel Database")
    
    risultati = []
    for entry in gs_entries:
        risultati.append({
            "url": entry.url,
            "domain": domain,
            "gold_text": entry.gold_text
        })
    return {"gold_standard": risultati}


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
            parsed_data = await get_parsed_data(entry.url)
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
