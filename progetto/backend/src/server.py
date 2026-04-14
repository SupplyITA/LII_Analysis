import json
import os
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from typing import List, Dict, Optional
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

app = FastAPI()

# --- I TUOI MODELLI PYDANTIC ---

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
    x_eval: Optional[Dict] = {} # Aggiunto per flessibilità

class EvaluateRequest(BaseModel):
    parsed_text : str
    gold_text: str

# --- LOGICA DI SUPPORTO ---

def load_domains():
    with open("../domains.json", "r") as f:
        return json.load(f)["domains"]

# --- I TUOI ENDPOINT CON LA LOGICA INSERITA ---

@app.get("/parse", response_model=ParseResponse)
async def parse(url: str):
    domains = load_domains()
    # Controllo se il dominio è supportato [cite: 466]
    if not any(d in url for d in domains):
        raise HTTPException(status_code=400, detail="Dominio non supportato")
    
    # Logica Crawl4AI [cite: 172-181]
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        if not result.success:
            raise HTTPException(status_code=404, detail="URL irraggiungibile")
        
        return ParseResponse(
            url=url,
            domain=next(d for d in domains if d in url),
            title="Titolo da estrarre", 
            html_text=result.html,
            parsed_text=result.markdown
        )

@app.get("/domains")
def get_domains():
    return {"domains": load_domains()} [cite: 497-501]

@app.get("/gold_standard")
def get_gold_standard(url: str): # Corretto da 'domain' a 'url' come da specifica 
    domains = load_domains()
    for d in domains:
        path = f"../gs_data/{d}_gs.json"
        if os.path.exists(path):
            with open(path, "r") as f:
                gs_list = json.load(f)
                for entry in gs_list:
                    if entry["url"] == url:
                        return entry
    raise HTTPException(status_code=404, detail="URL non trovato nel GS")

@app.post("/evaluate", response_model=EvaluationResponse)
def evaluate(request: EvaluateRequest):
    # Logica token_level_eval (minuscolo e split per spazi) [cite: 428-438]
    tokens_p = set(request.parsed_text.lower().split())
    tokens_g = set(request.gold_text.lower().split())
    
    inter = len(tokens_p.intersection(tokens_g))
    prec = inter / len(tokens_p) if tokens_p else 0
    rec = inter / len(tokens_g) if tokens_g else 0
    f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0
    
    return {
        "token_level_eval": {
            "precision": round(prec, 2),
            "recall": round(rec, 2),
            "f1": round(f1, 2)
        }
    }
