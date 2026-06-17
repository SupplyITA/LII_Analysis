import json, os, re, html, urllib.request
from urllib.parse import urlparse
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Depends
from typing import List, Dict, Optional, Any
import mistune
from bs4 import BeautifulSoup
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from src.database import get_db
from src.models import WebResource, GoldStandard, Evaluation, JudgeEvaluation
from src.init_db import init_db

from src.logic.metrics import compute_token_level_eval
from src.logic.gs_manager import load_domains 
from src.logic.parser_wikipedia import parser_wikipedia
from src.logic.parser_grammy import parser_grammy
from src.logic.parser_huddle import parser_huddle
from src.logic.parser_academia import parser_academia
from src.logic.llm_judge import evaluate_with_llm

class URLRequest(BaseModel):
    url: str

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

class ParseRequest(BaseModel):
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
    judge_score: Optional[float] = 0.0
    x_eval: Optional[Dict] = {} 

class EvaluateRequest(BaseModel):
    """ Input richiesto per endpoint di valutazione """
    parsed_text : str
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
    """  Rimuove il Markdown da una stringa, restituendo solo il testo pulito """
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
    
    return {"url": url, "domain": "unknown", "title": "Not Found", "html_text": html_text or "", "parsed_text": html_text or ""}


# ---------------------------- Endpoint ----------------------------

@app.get("/domains")
def get_domains():
    """ Restituisce la lista dei domini supportati """
    return {"domains": load_domains()}

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
        if not result or "parsed_text" not in result:
            result = {"url": request.url, "domain": "unknown", "title": "", "html_text": "", "parsed_text": "Testo non trovato"}
        
        # salvataggio se risorsa nuova e non locale
        if not request.local:
            existing = db.query(WebResource).filter(WebResource.url == request.url).first()    
            if not existing:
                db.add(
                    WebResource(url=result["url"], 
                    domain=result["domain"], 
                    title=result["title"], 
                    html_text=result["html_text"]))
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
        "title": gs_entry.web_resource.title if gs_entry.web_resource else "",
        "html_text": gs_entry.web_resource.html_text if gs_entry.web_resource else "",
        "gold_text": gs_entry.gold_text
    }

@app.get("/gold_standard_urls")
def get_gold_standard_urls(domain:str, db: Session = Depends(get_db)):
    """ Restituisce la lista di tutti gli URL presenti nel GS per un dominio """
    if domain not in load_domains():
        raise HTTPException(status_code=400, detail="Dominio non supportato")
    # join tra gs e webresource per filtrare un dominio
    urls = db.query(GoldStandard.url).join(WebResource).filter(WebResource.domain == domain).all()
    return {"gold_standard_urls": [u[0] for u in urls] if urls else []}

@app.post("/evaluate", response_model=EvaluationResponse)
def evaluate(request: EvaluateRequest):
    """ Confronta un testo parsato con il gold standard e restituisce le metriche di valutazione  """
    clean_parsed_text = remove_markdown(request.parsed_text)
    metrics = compute_token_level_eval(clean_parsed_text, request.gold_text)
    return {"token_level_eval": metrics, "judge_score": 0.0}


# modificato qquesto endpoint !
@app.get("/full_gs_eval", response_model=EvaluationResponse)
async def full_gs_eval(domain: str, db: Session = Depends(get_db)):
    """ Valutazione complessiva leggendo dal database """
    if domain not in load_domains():
        raise HTTPException(status_code=400, detail="Dominio non supportato")
    
    gs_entries = db.query(GoldStandard).join(WebResource).filter(WebResource.domain == domain).all()
    
    if not gs_entries:
        return {"token_level_eval": {"precision": 0.0, "recall": 0.0, "f1": 0.0}, "judge_score": 0.0}
    
    results_metrics = []
    results_scores = []
    
    for entry in gs_entries:
        try:
            # prende html dal db e lo parsa
            html_salvato = entry.web_resource.html_text if entry.web_resource else None
            parsed_data = await get_parsed_data(entry.url, html_text=html_salvato) 

            if parsed_data:
                raw_md = parsed_data.get("parsed_text", "")
                clean_parsed_text = remove_markdown(raw_md)

                # calcolo metriche
                metrics = compute_token_level_eval(clean_parsed_text, entry.gold_text)
                results_metrics.append(metrics)

                # judge evaluation - llm
                ia_res = await evaluate_with_llm(clean_parsed_text, entry.gold_text)
                score = ia_res.get("score", 1) 
                results_scores.append(score)
    
                # salvataggio statistiche pre-calcolate
                db.query(Evaluation).filter(Evaluation.url == entry.url).delete()
                db.query(JudgeEvaluation).filter(JudgeEvaluation.url == entry.url).delete()

                db.add(Evaluation(
                    url=entry.url,
                    precision_score=metrics["precision"],
                    recall_score = metrics["recall"],
                    f1_score = metrics["f1"]
                ))
                
                db.add(JudgeEvaluation(
                    url=entry.url, 
                    model_name="llama3.2:3b", 
                    score=score, 
                    feedback=ia_res.get("feedback", "")
                ))

        except Exception as e:
            print(f"Errore su {entry.url}: {str(e)}")
            continue    # per non bloccare tutto il processo
    
    # commit delle valutazioni nel db
    db.commit()

    if not results_metrics:
        raise HTTPException(status_code=500, detail="Impossibile calcolare valutazioni per il dominio")
        # return {"token_level_eval": {"precision": 0.0, "recall": 0.0, "f1": 0.0}, "judge_score": 0.0}

    # calcolo metriche aggregate
    avg_precision = sum(r["precision"] for r in results_metrics) / len(results_metrics)
    avg_recall = sum(r["recall"] for r in results_metrics) / len(results_metrics)
    avg_f1 = sum(r["f1"] for r in results_metrics) / len(results_metrics)
    avg_judge = sum(results_scores) / len (results_scores) if results_scores else 0.0
       
    return {
        "token_level_eval": {
            "precision": round(avg_precision, 4),
            "recall": round(avg_recall, 4),
            "f1": round(avg_f1, 4)
        },
        "judge_score": round(avg_judge, 2),
        # ?
        "x_eval": {}
        }

@app.post("/evaluate_judge", response_model=JudgeResponse)
async def evaluate_judge(request: EvaluateRequest):
    """ Invia il testo a Ollama per una valutazione """    
    try:
        clean_parsed_text = remove_markdown(request.parsed_text)
        res_ia = await evaluate_with_llm(clean_parsed_text, request.gold_text)
        
        return JudgeResponse(model_name="llama3.2:3b", 
                             judge_score=res_ia.get("score", 1), 
                             judge_feedback=res_ia.get("feedback", "Nessun feedback disponibile")
        )
    except Exception as e:
        return JudgeResponse(model_name="error", 
                             judge_score=1, 
                             judge_feedback=str(e)
        )

@app.get("/db_stats")
def get_db_stats(db: Session = Depends(get_db)):
    """ Restituisce conteggi e medie pre-calcolate per dominio """
    domains = load_domains()

    # inizializzazione strutture dati per tutti i domini
    wr_counts = {d: 0 for d in domains}
    gs_counts = {d: 0 for d in domains}
    avg_eval_dict = {d: {"token_level_eval":{"precision": 0.0, "recall": 0.0, "f1": 0.0}} for d in domains}
    avg_eval_judge_dict = {d: {"judge_score":0.0} for d in domains}

    # conteggio web resources
    wr_stats = db.query(WebResource.domain, func.count(WebResource.url)).group_by(WebResource.domain).all()
    for dom, count in wr_stats:
        if dom in wr_counts: wr_counts[dom] = count

    # conteggio gold standard
    gs_stats = db.query(WebResource.domain, func.count(GoldStandard.url)).join(GoldStandard, WebResource.url == GoldStandard.url).group_by(WebResource.domain).all()
    for dom, count in gs_stats:
        if dom in gs_counts: gs_counts[dom] = count

    # calcolo metriche
    for d in domains:
        # metriche prese dalla tabella Evaluation
        metrics_avg = db.query(
            func.avg(Evaluation.precision_score),
            func.avg(Evaluation.recall_score),
            func.avg(Evaluation.f1_score)            
        ).join(WebResource, Evaluation.url == WebResource.url).filter(WebResource.domain == d).first()

        if metrics_avg and metrics_avg[0] is not None:
            avg_eval_dict[d]["token_level_eval"] = {
                "precision": round(metrics_avg[0], 4),
                "recall": round(metrics_avg[1], 4),
                "f1": round(metrics_avg[2], 4)
            }
        
        # media judge dalla tabella JudgeEvaluation
        judge_avg = db.query(
            func.avg(JudgeEvaluation.score)
        ).join(WebResource, JudgeEvaluation.url == WebResource.url).filter(WebResource.domain == d).scalar()

        if judge_avg is not None:
            avg_eval_judge_dict[d]["judge_score"] = round(float(judge_avg), 2)

    return {
        "web_resources": wr_counts,
        "gold_standard": gs_counts,
        "avg_eval": avg_eval_dict,   
        "avg_eval_judge": avg_eval_judge_dict  
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
        db.execute(text("SELECT 1")) 
    except:
        status["database"] = "error"

    # controllo ollama
    try:
        urllib.request.urlopen("http://ollama:11434/", timeout=2)
    except:
        status["ollama"] = "error"

    return status

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
        raise HTTPException(status_code=400, detail="WebResource non esistente. Impossibile inserire GoldStandard") # Blocco inserimentose non esiste risorsa
        #db.add(WebResource(url=gs.url, domain="unknown", title="", html_text=""))
        #db.commit()
        
    if not db.query(GoldStandard).filter(GoldStandard.url == gs.url).first():
        db.add(GoldStandard(url=gs.url, gold_text=gs.gold_text))
        db.commit()
    return {"status": "ok"}

@app.delete("/web_resource")
def delete_web_resource(req: URLRequest, db: Session = Depends(get_db)):
    db.query(GoldStandard).filter(GoldStandard.url == req.url).delete()
    db.query(WebResource).filter(WebResource.url == req.url).delete()
    db.commit()
    return {"status": "ok"}

@app.delete("/gold_standard")
def delete_gold_standard(req: URLRequest, db: Session = Depends(get_db)):
    db.query(GoldStandard).filter(GoldStandard.url == req.url).delete()
    db.commit()
    return {"status": "ok"}
