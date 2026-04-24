import json
import os
import re
from urllib.parse import urlparse
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from typing import List, Dict, Optional
import mistune
import html
from bs4 import BeautifulSoup

from src.logic.metrics import compute_token_level_eval
from src.logic.gs_manager import load_domains, find_url_in_gs, load_full_domain_gs
from src.logic.parser_wikipedia import parser_wikipedia
from src.logic.parser_grammy import parser_grammy
from src.logic.parser_huddle import parser_huddle
from src.logic.parser_academia import parser_academia

app = FastAPI()

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
        
    text = html.unescape(str(soup))#nuova
        
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

@app.get("/parse", response_model = ParseResponse)
async def parse(url: str):
    """ Scarica un URL e ne estrae il contenuto pulito """
    supported_domains = load_domains()
    if not any(d in url for d in supported_domains):
        raise HTTPException(status_code=400, detail="Dominio non supportato")

    try:
        result = await get_parsed_data(url)
        if not result:
            raise HTTPException(status_code=400, detail="Parser specifico non trovato")
        return result
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"URL irraggiungibile o errore di parsing: {str(e)}")
    
@app.post("/parse", response_model=ParseResponse)
async def parse_post(request: ParseHtmlRequest):
    """ Esegue il parser su un testo HTML fornito direttamente """
    supported_domains = load_domains()
    if not any(d in request.url for d in supported_domains):
        raise HTTPException(status_code=400, detail="Dominio non supportato")
    try:
        result = await get_parsed_data(request.url, html_text=request.html_text)
        if not result:
            raise HTTPException(status_code=400, detail="Parser specifico non trovato")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore di parsing sull'HTML fornito: {str(e)}")


@app.get("/gold_standard")
def get_gold_standard(url: str): 
    """ Restituisce il gold standard di un documento per l'url dato in input """
    entry = find_url_in_gs(url)

    if not entry:
        raise HTTPException(status_code=404, detail="URL non trovato nel GS")
    return entry

@app.get("/full_gold_standard")
def get_full_gold_standard(domain: str):
    """ Restituisce la lista degli elementi di un gold standard per il dominio dato in input """
    gs_data = load_full_domain_gs(domain)
    
    if gs_data is None:
        raise HTTPException(status_code = 404, detail = "Dominio non supportat o GS mancante")
    
    return {"gold_standard": gs_data}

@app.post("/evaluate", response_model=EvaluationResponse)
def evaluate(request: EvaluateRequest):
    """ Confronta un testo parsato con il gold standard e restituisce le metriche di valutazione  """
    clean_parsed_text = remove_markdown(request.parsed_text)
    metrics = compute_token_level_eval(clean_parsed_text, request.gold_text)
    return {"token_level_eval": metrics}

@app.get("/full_gs_eval", response_model=EvaluationResponse)
async def full_gs_eval(domain: str):
    """ Restituisce la valutazione complessiva del gold standard per il dominio dato in input"""
    gs_entries = load_full_domain_gs(domain)
    
    if not gs_entries:
        raise HTTPException(status_code=404, detail="Dominio non trovato")
    
    results = []
    for entry in gs_entries:
        try:
            url = entry["url"]

            parsed_data = await get_parsed_data(url)
            
            if parsed_data:
                raw_md = parsed_data.get("parsed_text", "")
                clean_parsed_text = remove_markdown(raw_md)
                metrics = compute_token_level_eval(clean_parsed_text, entry["gold_text"])
                results.append(metrics)
        except Exception as e:
            print(f"Errore su {url}: {str(e)}")
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
