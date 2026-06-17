import os
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
import requests
from urllib.parse import urlparse
import re

app = FastAPI()

# Percorso relativo dinamico
BASE_DIR = os.path.dirname(__file__)
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "..", "templates"))

# URL del backend 
BACKEND_URL = "http://backend:8003" 

# -------------------- Homepage
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    error_msg = None
    try:        
        status = requests.get(f"{BACKEND_URL}/status", timeout=5).json()
        domains = requests.get(f"{BACKEND_URL}/domains", timeout=5).json().get("domains", [])
    except Exception:
        status = {"backend": "error", "database": "error", "ollama": "error"}
        domains = []
        error_msg = "Impossibile contattare il Backend."
    
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={
            "request": request,
            "status": status,
            "domains": domains,
            "error": error_msg
        }
    )


# -------------------- Pagina di parser + evaluation
@app.get("/evaluation", response_class=HTMLResponse)
def evaluation_page(request: Request):
    all_urls = []
    error_msg = None
    try:
        domains_resp = requests.get(f"{BACKEND_URL}/domains", timeout=5)
        if domains_resp.status_code == 200:
            for d in domains_resp.json().get("domains", []):
                resp = requests.get(f"{BACKEND_URL}/gold_standard_urls", params={"domain": d}, timeout=5)
                if resp.status_code == 200:
                    all_urls.extend(resp.json().get("gold_standard_urls", []))
        else:
            error_msg = domains_resp.json().get("detail", "Errore nel recupero domini")
    except Exception: 
        error_msg = "Backend non raggiungibile."

    return templates.TemplateResponse(
        request=request,
        name="evaluation.html", 
        context={
            "request": request, 
            "gs_urls": all_urls, 
            "result": None, 
            "error": error_msg
        }
    )


@app.post("/evaluation", response_class=HTMLResponse)
def evaluate_parser(request: Request, url: str = Form(...), local: bool = Form(False)):
    all_urls = []
    try:
        domains = requests.get(f"{BACKEND_URL}/domains", timeout=5).json().get("domains", [])
        for d in domains:
            resp = requests.get(f"{BACKEND_URL}/gold_standard_urls", params={"domain": d}, timeout=5).json()
            all_urls.extend(resp.get("gold_standard_urls", []))
    except Exception:
        pass

    try:
        # AUMENTATO IL TIMEOUT PER IL CRAWLER LIVE A 60s
        parse_resp = requests.post(f"{BACKEND_URL}/parse", json={"url": url, "local": local}, timeout=60)
        if parse_resp.status_code != 200:
            error_detail = parse_resp.json().get("detail", "Errore durante il parsing dell'URL.")
            return templates.TemplateResponse(request=request, name="evaluation.html", context={"request": request, "error": error_detail, "gs_urls": all_urls})
        
        parse_data = parse_resp.json()

        gs_data = None
        metrics = None
        judge = None
        gs_resp = requests.get(f"{BACKEND_URL}/gold_standard", params={"url": url}, timeout=5)

        if gs_resp.status_code == 200:
            gs_data = gs_resp.json()

            # valutazione matematica
            eval_resp = requests.post(f"{BACKEND_URL}/evaluate", json={
                "parsed_text": parse_data["parsed_text"],
                "gold_text": gs_data["gold_text"]
            }, timeout=5)
            metrics = eval_resp.json().get("token_level_eval") if eval_resp.status_code == 200 else None

            # valutazione judge
            judge_resp = requests.post(f"{BACKEND_URL}/evaluate_judge", json={
                "parsed_text": parse_data["parsed_text"],
                "gold_text": gs_data["gold_text"]
            }, timeout=30)  
            judge = judge_resp.json() if judge_resp.status_code == 200 else None

        result = {
            "url": url,
            "title": parse_data.get("title"),
            "html_text": parse_data.get("html_text"),
            "parsed_text": parse_data.get("parsed_text"),
            "gold_text": gs_data.get("gold_text") if gs_data else None,
            "metrics": metrics,
            "judge": judge
        }
        return templates.TemplateResponse(request=request, name="evaluation.html", context={"request": request, "result": result, "gs_urls": all_urls})

    except Exception as e:
        return templates.TemplateResponse(request=request, name="evaluation.html", context={"request": request, "error": str(e), "gs_urls": all_urls})


# -------------------- Pagina gold standard builder
@app.get("/gs_builder", response_class=HTMLResponse)
def gs_builder_page(request: Request, domain: str = None):
    domains = []
    urls_in_gs = []
    error_msg = None
    try:
        domains_resp = requests.get(f"{BACKEND_URL}/domains", timeout=5)
        if domains_resp.status_code == 200:
            domains = domains_resp.json().get("domains", [])
        
        if domain:
            resp = requests.get(f"{BACKEND_URL}/gold_standard_urls", params={"domain": domain}, timeout=5)
            if resp.status_code == 200:
                urls_in_gs = resp.json().get("gold_standard_urls", [])
            else:
                error_msg = resp.json().get("detail", "Errore recupero URL del dominio")
    except Exception:
        error_msg = "Backend non raggiungibile"
    
    return templates.TemplateResponse(
        request=request,
        name="gs-builder.html", 
        context={
            "request": request, 
            "domains": domains, 
            "selected_domain": domain,
            "urls_in_gs": urls_in_gs,
            "error": error_msg
        }
    )

@app.post("/gs_builder/fetch_html")
def fetch_html(url: str = Form(...)):
    try:
        resp = requests.post(f"{BACKEND_URL}/parse", json={"url": url, "local": False}, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            return {"html_text": data.get("html_text", ""), "url": url}
        return {"error": resp.json().get("detail", "Impossibile scaricare l'HTML o dominio non supportato")}
    except Exception as e:
        return {"error": f"Errore di connessione al Backend: {str(e)}"}

@app.post("/gs_builder/add")
def add_gs(request: Request, url: str = Form(...), html_text: str = Form(...), gold_text: str = Form(...)):
    try:
        # RISOLUZIONE BUG PAYLOAD: Estrae dominio e titolo per soddisfare i requisiti del backend
        domain = urlparse(url).netloc
        title_match = re.search(r'<title>(.*?)</title>', html_text, re.IGNORECASE)
        title = title_match.group(1) if title_match else "No Title Found"

        payload_web_res = {
            "url": url, 
            "domain": domain, 
            "title": title, 
            "html_text": html_text
        }

        # TIMEOUT ALZATI A 15s E PAYLOAD COMPLETO INVIATO AL DB
        res1 = requests.post(f"{BACKEND_URL}/add_web_resource", json=payload_web_res, timeout=15)
        if res1.status_code not in (200, 201) and "already exists" not in res1.text:
             return templates.TemplateResponse(request=request, name="gs-builder.html", context={"request": request, "error": f"Errore aggiunta web_resource: {res1.text}"})
        
        res2 = requests.post(f"{BACKEND_URL}/add_gold_standard", json={"url": url, "gold_text": gold_text}, timeout=15)
        if res2.status_code not in (200, 201):
             return templates.TemplateResponse(request=request, name="gs-builder.html", context={"request": request, "error": f"Errore aggiunta gold_standard: {res2.text}"})
             
    except Exception as e:
        return templates.TemplateResponse(request=request, name="gs-builder.html", context={"request": request, "error": f"Errore di connessione: {str(e)}"})
        
    return RedirectResponse(url="/gs_builder", status_code=303)


class DeleteRequest(BaseModel):
    url: str

@app.delete("/web_resource")
def delete_url(payload: DeleteRequest):
    try:
        resp = requests.delete(f"{BACKEND_URL}/web_resource", json={"url": payload.url}, timeout=5)
        if resp.status_code == 200:
            return {"status": "ok"}
        return {"error": resp.json().get("detail", "Errore durante l'eliminazione")}
    except Exception:
        return {"error": "Backend non raggiungibile"}


# -------------------- Pagina stats
@app.get("/stats", response_class=HTMLResponse)
def stats_page(request: Request):
    stats = {}
    error_msg = None
    try:
        resp = requests.get(f"{BACKEND_URL}/db_stats", timeout=5)
        if resp.status_code == 200:
            stats = resp.json()
        else:
            error_msg = resp.json().get("detail", "Errore nel recupero statistiche dal DB")
    except Exception:
        error_msg = "Backend non raggiungibile"
        
    return templates.TemplateResponse(
        request=request, 
        name="stats.html", 
        context={"request": request, "stats": stats, "error": error_msg}
    )