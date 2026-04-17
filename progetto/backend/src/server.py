import json
import os
from urllib.parse import urlparse
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from typing import List, Dict, Optional
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

from src.logic.metrics import compute_token_level_eval
from src.logic.gs_manager import load_domains, find_url_in_gs, load_full_domain_gs
from src.logic.parser_wikipedia import parse_wikipedia
from src.logic.parser_reddit import parse_reddit
from src.logic.parser_stackoverflow import parse_stackoverflow
from src.logic.parser_grammy import parse_grammy
from src.logic.parser_huddle import  parse_huddle
from src.logic.parser_academia import parse_academia

app = FastAPI()

class ParseResponse(BaseModel):
    url: str
    domain: str
    title: str
    html_text: str
    parsed_text: str

class TokenLevelEval(BaseModel):
    precision: float
    recall: float
    f1: float
    
class EvaluationResponse(BaseModel):
    token_level_eval: TokenLevelEval
    x_eval: Optional[Dict] = {} 

class EvaluateRequest(BaseModel):
    parsed_text : str
    gold_text: str


# -- Endpoint --

''' Restituisce la lista dei domini assegnati '''
@app.get("/domains")
def get_domains():
    return {"domains": load_domains()}

''' Sceglie il parser giusto in base al dominio e restituisce i dati parsati'''
async def get_parsed_data(url: str):
    netloc = urlparse(url).netloc.lower()
    
    if "wikipedia.org" in netloc:
        return await parse_wikipedia(url)
    elif "stackoverflow.com" in netloc:
        return await parse_stackoverflow(url)
    elif "reddit.com" in netloc:
        return await parse_reddit(url)
    elif "huddle.org" in netloc:
        return await parse_huddle(url)
    elif "grammy.com" in netloc:
        return await parse_grammy(url)
    elif "academia.edu" in netloc:
        return await parse_academia(url)
    return None


''' Esegue il parser per un documento di un dominio '''
@app.get("/parse", response_model = ParseResponse)
async def parse(url: str):
    supported_domains = load_domains()

    if not any (d in url for d in supported_domains):
        raise HTTPException(status_code=400, detail="Dominio non supportato")

    try:
        result = await get_parsed_data(url)
        if not result:
            raise HTTPException(status_code = 400, detail = "Parser specificonon trovato")
        return result
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"URL irraggiungibile o errore di parsing: {str(e)}")


''' Restituisce il gold standard per un documento '''
@app.get("/gold_standard")
def get_gold_standard(url: str): 
    entry = find_url_in_gs(url)

    if not entry:
        raise HTTPException(status_code=404, detail="URL non trovato nel GS")
    return entry


''' Restituisce tutto il gs del dominio '''
@app.get("/full_gold_standard")
def get_full_gold_standard(domain: str):
    gs_data = load_full_domain_gs(domain)
    
    if gs_data is None:
        raise HTTPException(status_code = 404, detail = "Dominio non supportat o GS mancante")
    
    return {"gold_standard": gs_data}


''' Valuta il parsing rispetto al gs'''
@app.post("/evaluate", response_model=EvaluationResponse)
def evaluate(request: EvaluateRequest):
    metrics = compute_token_level_eval(request.parsed_text, request.gold_text)
    return {"token_level_eval": metrics}


''' Restituisce valutazione complessiva del gs per un dominio '''
@app.get("/full_gs_eval", response_model = EvaluationResponse)
async def full_gs_eval(domain: str):
    gs_entries = load_full_domain_gs(domain)
    
    if not gs_entries:
        raise HTTPException(status_code = 404, detail = "Dominio non trovato")
    
    results = []
    for entry in gs_entries:
        try:
            url = entry["url"]
            parsed_data = await get_parsed_data(url)
            if parsed_data:
                metrics = compute_token_level_eval(parsed_data["parsed_text"], entry["gold_text"])
                results.append(metrics)
        except Exception:
            continue    # se un url fallisce si passa al prossimo

    if not results:
        raise HTTPException(status_code=500, detail="Impossibile valutare il dominio") 

    # valutare se spostarle
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