import json
import os
import re
from urllib.parse import urlparse
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from typing import List, Dict, Optional
import mistune
from bs4 import BeautifulSoup

from src.logic.metrics import compute_token_level_eval
from src.logic.gs_manager import load_domains, find_url_in_gs, load_full_domain_gs
from src.logic.parser_wikipedia import parser_wikipedia
from src.logic.parser_reddit import parser_reddit
from src.logic.parser_stackoverflow import parser_stackoverflow
from src.logic.parser_grammy import parser_grammy
from src.logic.parser_huddle import parser_huddle
from src.logic.parser_academia import parser_academia

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

# aggiunta per il requisito più recente !!!
class ParseHtmlRequest(BaseModel):
    url: str
    html_text: str

def remove_markdown(md: str) -> str:
    html = mistune.html(md)
    soup = BeautifulSoup(html, "html.parser")
    
    for tag in soup.find_all(True):
        tag.unwrap()
        
    text = re.sub(r'[ \t]+', ' ', str(soup)) 
    text = re.sub(r'\n+', '\n', text) 
    return text.strip()

async def get_parsed_data(url: str, html_text: str = None):
    
    netloc = urlparse(url).netloc.lower()
    
    if "wikipedia.org" in netloc:
        return await parser_wikipedia(url, html_raw=html_text)
    elif "stackoverflow.com" in netloc:
        return await parser_stackoverflow(url, html_raw=html_text)
    elif "reddit.com" in netloc:
        return await parser_reddit(url, html_raw=html_text)
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
    return {"domains": load_domains()}


@app.get("/parse", response_model = ParseResponse)
async def parse(url: str):
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
    supported_domains = load_domains()
    if not any(d in request.url for d in supported_domains):
        raise HTTPException(status_code=400, detail="Dominio non supportato")
    try:
        # Passiamo sia l'URL che l'HTML grezzo ai nostri parser
        result = await get_parsed_data(request.url, html_text=request.html_text)
        if not result:
            raise HTTPException(status_code=400, detail="Parser specifico non trovato")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore di parsing sull'HTML fornito: {str(e)}")


@app.get("/gold_standard")
def get_gold_standard(url: str): 
    entry = find_url_in_gs(url)

    if not entry:
        raise HTTPException(status_code=404, detail="URL non trovato nel GS")
    return entry

@app.get("/full_gold_standard")
def get_full_gold_standard(domain: str):
    gs_data = load_full_domain_gs(domain)
    
    if gs_data is None:
        raise HTTPException(status_code = 404, detail = "Dominio non supportat o GS mancante")
    
    return {"gold_standard": gs_data}

@app.post("/evaluate", response_model=EvaluationResponse)
def evaluate(request: EvaluateRequest):
    clean_parsed_text = remove_markdown(request.parsed_text)
    metrics = compute_token_level_eval(clean_parsed_text, request.gold_text)
    return {"token_level_eval": metrics}

@app.get("/full_gs_eval", response_model=EvaluationResponse)
async def full_gs_eval(domain: str):
    gs_entries = load_full_domain_gs(domain)
    
    if not gs_entries:
        raise HTTPException(status_code=404, detail="Dominio non trovato")
    
    results = []
    for entry in gs_entries:
        try:
            url = entry["url"]
            parsed_data = await get_parsed_data(url)
            if parsed_data:
                clean_parsed_text = remove_markdown(parsed_data["parsed_text"])
                metrics = compute_token_level_eval(clean_parsed_text, entry["gold_text"])
                results.append(metrics)
        except Exception:
            continue

    if not results:
        raise HTTPException(status_code=500, detail="Impossibile valutare il dominio") 

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
