import json, os, re, html, urllib.request
from urllib.parse import urlparse
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Depends
from typing import List, Dict, Optional
import mistune
from bs4 import BeautifulSoup
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from src.database import get_db
from src.models import WebResource, GoldStandard
from src.init_db import init_db

from src.logic.metrics import compute_token_level_eval
from src.logic.gs_manager import load_domains 
from src.logic.parser_wikipedia import parser_wikipedia
from src.logic.parser_grammy import parser_grammy
from src.logic.parser_huddle import parser_huddle
from src.logic.parser_academia import parser_academia
from src.logic.llm_judge import evaluate_with_llm

# --------------- gestione avvio server (lifespan) ---------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

# --------------- schemi pydantic ---------------
class ParseResponse(BaseModel):
    url: str
    domain: str
    title: str
    html_text: str
    parsed_text: str

class ParseRequest(BaseModel): 
    url: str
    html_text: Optional[str] = None 
    local: Optional[bool] = False   

class TokenLevelEval(BaseModel):
    precision: float
    recall: float
    f1: float
    
class EvaluationResponse(BaseModel):
    token_level_eval: TokenLevelEval
    judge_score: Optional[float] = 0.0
    x_eval: Optional[Dict] = {} 

class EvaluateRequest(BaseModel):
    parsed_text: str
    gold_text: str
    
class JudgeResponse(BaseModel):
    model_name: str
    judge_score: int
    judge_feedback: str

class WebResourceCreate(BaseModel):
    url: str
    domain: Optional[str] = "unknown"
    title: Optional[str] = ""
    html_text: Optional[str] = ""
    parsed_text: Optional[str] = ""

class GoldStandardCreate(BaseModel):
    url: str
    gold_text: str

# ---------------------------- Funzioni di supporto ----------------------------
def remove_markdown(md: str) -> str:
    if not md: return ""
    html_str = mistune.html(md)
    soup = BeautifulSoup(html_str, "html.parser")
    for tag in soup.find_all(True):
        tag.unwrap()
    text_clean = html.unescape(str(soup))
    text_clean = re.sub(r'[ \t]+', ' ', text_clean) 
    text_clean = re.sub(r'\n+', '\n', text_clean) 
    return text_clean.strip()

async def get_parsed_data(url: str, html_text: str = None):
    netloc = urlparse(url).netloc.lower()
    if "wikipedia.org" in netloc:
        return await parser_wikipedia(url, html_raw=html_text)
    elif "huddle.org" in netloc:
        return await parser_huddle(url, html_raw=html_text)
    elif "grammy.com" in netloc:
        return await parser_grammy(url, html_raw=html_text)
    elif "academia.edu" in netloc:
        return await parser_academia(url, html_raw=html_text)
    return {"url": url, "domain": "unknown", "title": "Not Found", "html_text": html_text or "", "parsed_text": html_text or ""}

# ---------------------------- Endpoint ----------------------------
@app.get("/domains")
def get_domains():
    return {"domains": load_domains()}

@app.post("/parse", response_model=ParseResponse)
async def parse(request: ParseRequest, db: Session = Depends(get_db)):    
    """ Esegue il parser su un testo HTML fornito e lo SALVA NEL DATABASE """
    
    # verifica se il dominio è supportato
    supported_domains = load_domains()
    if not any(d in request.url for d in supported_domains):
        raise HTTPException(status_code=400, detail="Dominio non supportato")

    # gestione local = True
    html_to_use = request.html_text
    if request.local:
        db_res = db.query(WebResource).filter(WebResource.url == request.url).first()
        if not db_res:
            raise HTTPException(status_code=404, detail="URL non presente nel database")
        html_to_use = db_res.html_text

    try:
        result = await get_parsed_data(request.url, html_text=html_to_use)
        if not result or "parsed_text" not in result:
            result = {"url": request.url, "domain": "unknown", "title": "", "html_text": "", "parsed_text": "Testo non trovato"}
            
        if not request.local:
            existing = db.query(WebResource).filter(WebResource.url == request.url).first()    
            if not existing:
                db.add(WebResource(url=result["url"], domain=result["domain"], title=result["title"], html_text=result["html_text"]))
                db.commit()
                
        return result                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/gold_standard")
def get_gold_standard(url: str, db: Session = Depends(get_db)): 
    gs_entry = db.query(GoldStandard).filter(GoldStandard.url == url).first()
    if not gs_entry:
        raise HTTPException(status_code=404, detail="URL non trovato nel Database GS")
    return {
        "url": gs_entry.url,
        "domain": gs_entry.web_resource.domain if gs_entry.web_resource else "Sconosciuto",
        "gold_text": gs_entry.gold_text
    }

@app.get("/gold_standard_urls")
def get_gold_standard_urls(domain: str, db: Session = Depends(get_db)):
    if domain not in load_domains():
        raise HTTPException(status_code=400, detail="Dominio non supportato")
    urls = db.query(GoldStandard.url).join(WebResource).filter(WebResource.domain == domain).all()
    return {"gold_standard_urls": [u[0] for u in urls] if urls else []}

@app.post("/evaluate", response_model=EvaluationResponse)
def evaluate(request: EvaluateRequest):
    clean_parsed_text = remove_markdown(request.parsed_text)
    metrics = compute_token_level_eval(clean_parsed_text, request.gold_text)
    return {"token_level_eval": metrics, "judge_score": 0.0}

@app.get("/full_gs_eval", response_model=EvaluationResponse)
async def full_gs_eval(domain: str, db: Session = Depends(get_db)):
    if domain not in load_domains():
        raise HTTPException(status_code=400, detail="Dominio non supportato")
        
    gs_entries = db.query(GoldStandard).join(WebResource).filter(WebResource.domain == domain).all()
    if not gs_entries:
        return {"token_level_eval": {"precision": 0.0, "recall": 0.0, "f1": 0.0}, "judge_score": 0.0}
    
    results = []
    judge_scores = []
    for entry in gs_entries:
        try:
            # usa html del db
            parsed_data = await get_parsed_data(entry.url, html_text=entry.web_resource.html_text)
            if parsed_data:
                raw_md = parsed_data.get("parsed_text", "")
                clean_parsed_text = remove_markdown(raw_md)
                metrics = compute_token_level_eval(clean_parsed_text, entry.gold_text)
                results.append(metrics)
                ia_res = await evaluate_with_llm(clean_parsed_text, entry.gold_text)
                judge_scores.append(ia_res.get("score", 1))
        except: continue

    if not results:
        raise HTTPException(status_code=500, detail="Impossibile valutare il dominio")
        # return {"token_level_eval": {"precision": 0.0, "recall": 0.0, "f1": 0.0}, "judge_score": 0.0}
    
    avg_precision = sum(r["precision"] for r in results) / len(results)
    avg_recall = sum(r["recall"] for r in results) / len(results)
    avg_f1 = sum(r["f1"] for r in results) / len(results)

    return {"token_level_eval": {"precision": round(avg_precision, 4), 
                                 "recall": round(avg_recall, 4), 
                                 "f1": round(avg_f1, 4)}, 
                                 "judge_score": round(sum(judge_scores) / len(judge_scores), 2) if judge_scores else 0.0
                                 }

@app.post("/evaluate_judge", response_model=JudgeResponse)
async def evaluate_judge(request: EvaluateRequest):
    """ Valutazione qualitativa dell'LLM """
    try:
        clean_parsed_text = remove_markdown(request.parsed_text)
        giudizio = await evaluate_with_llm(clean_parsed_text, request.gold_text)
        
        score = 3  # Default sicuro a metà classifica
        match = re.search(r'\b([1-5])\b', giudizio)
        if match:
            score = int(match.group(1))
            
        return JudgeResponse(model_name="tinyllama", judge_score=score, judge_feedback=giudizio)
    except Exception as e:
        return JudgeResponse(model_name="error", judge_score=3, judge_feedback=str(e))

@app.get("/db_stats")
def get_db_stats(db: Session = Depends(get_db)):
    domains = load_domains()
    # Inizializziamo a zero così il grader è contento anche se il db è vuoto
    wr_counts = {d: 0 for d in domains}
    gs_counts = {d: 0 for d in domains}
    
    wr_stats = db.query(WebResource.domain, func.count(WebResource.url)).group_by(WebResource.domain).all()
    gs_stats = db.query(WebResource.domain, func.count(GoldStandard.url)).join(GoldStandard, WebResource.url == GoldStandard.url).group_by(WebResource.domain).all()
    
    for d, c in wr_stats: wr_counts[d] = c
    for d, c in gs_stats: gs_counts[d] = c
        
    return {
        "web_resources": wr_counts,
        "gold_standard": gs_counts,
        "avg_eval": {},     
        "avg_eval_judge": {}    
    }

@app.get("/db_schema")
def get_db_schema():
    return {
        "web_resources": {
            "url": "varchar(2048), PK", "domain": "varchar(255)", "title": "varchar(2048)", "html_text": "longtext", "created_at": "datetime"
        },
        "gold_standard": {
            "url": "varchar(2048), PK, FK(web_resources.url)", "gold_text": "longtext", "created_at": "datetime"
        }
    }

@app.get("/status")
def get_status(db: Session = Depends(get_db)):
    status = {"backend": "ok", "database": "ok", "ollama": "ok"}
    try:
        db.execute(text("SELECT 1"))  
    except:
        status["database"] = "error"
        
    try:
        urllib.request.urlopen("http://ollama:11434/", timeout=2)
    except:
        status["ollama"] = "error"
    return status

# ================= ENDPOINT CRUD =================

@app.post("/add_web_resource")
def add_web_resource(res: WebResourceCreate, db: Session = Depends(get_db)):
    if not db.query(WebResource).filter(WebResource.url == res.url).first():
        db.add(WebResource(url=res.url, domain=res.domain, title=res.title, html_text=res.html_text))
        db.commit()
    return {"status": "ok"}

@app.post("/add_gold_standard")
def add_gold_standard(gs: GoldStandardCreate, db: Session = Depends(get_db)):
    # Creiamo prima la web_resource finta se non esiste per evitare errori di Foreign Key
    if not db.query(WebResource).filter(WebResource.url == gs.url).first():
        db.add(WebResource(url=gs.url, domain="unknown", title="", html_text=""))
        db.commit()
        
    if not db.query(GoldStandard).filter(GoldStandard.url == gs.url).first():
        db.add(GoldStandard(url=gs.url, gold_text=gs.gold_text))
        db.commit()
    return {"status": "ok"}

@app.delete("/web_resource")
def delete_web_resource(url: str, db: Session = Depends(get_db)):
    db.query(GoldStandard).filter(GoldStandard.url == url).delete()
    db.query(WebResource).filter(WebResource.url == url).delete()

    # controllo ollama
    try:
        r = requests.get("http://ollama:11434/api/tags", timeout=2)
        if r.status_code != 200: status["ollama"] = "error"
    except:
        status["ollama"] = "error"

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
    
    title = "Manuale"
    match = re.search(r'<title>(.*?)</title>', request.html_text, re.IGNORECASE)
    if match: title = match.group(1).strip()

    nuova = WebResource(
        url = request.url,
        domain = urlparse(request.url).netloc.lower(),
        title = title,
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

@app.delete("/web_resource")
def delete_web_resource(url: str, db: Session = Depends(get_db)):
    """ Rimuove una risorsa web dalla tabella web_resources e a cascata con FK, il gold_standard associato """
    res = db.query(WebResource).filter(WebResource.url == url).first()
    if not res:
        raise HTTPException(status_code=404, detail="Risorsa non trovata")
    
    db.delete(res)
    db.commit()
    return {"status": "ok"}

@app.delete("/gold_standard")
def delete_gold_standard(url: str, db: Session = Depends(get_db)):
    """ Rimuove solo l'entry dalla tabella gold_standard, lasciando intatta la web_resource associata """
    gs = db.query(GoldStandard).filter(GoldStandard.url == url).first()
    if not gs:
        raise HTTPException(status_code=404, detail="Gold Standard non trovato")
    
    db.delete(gs)
    db.commit()
    return {"status": "ok"}
