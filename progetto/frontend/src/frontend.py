from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import requests
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# URL del backend (nel container Docker useremo il nome del servizio)
BACKEND_URL = "http://backend:8003" 

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Recupera i domini e gli URL del Gold Standard per il menu a tendina
    try:
        domains_resp = requests.get(f"{BACKEND_URL}/domains").json()
        domains = domains_resp.get("domains", [])
        
        all_gs_urls = []
        for d in domains:
            gs_resp = requests.get(f"{BACKEND_URL}/full_gold_standard?domain={d}").json()
            for entry in gs_resp.get("gold_standard", []):
                all_gs_urls.append(entry["url"])
    except Exception:
        all_gs_urls = []

    return templates.TemplateResponse("index.html", {
        "request": request, 
        "gs_urls": all_gs_urls,
        "result": None
    })

@app.post("/process", response_class=HTMLResponse)
async def process_url(request: Request, url: str = Form(...)):
    # 1. Chiamata al backend per il parsing
    parse_data = requests.get(f"{BACKEND_URL}/parse?url={url}").json()
    
    # 2. Controllo se l'URL è nel Gold Standard per mostrare il confronto
    gs_data = None
    metrics = None
    gs_resp = requests.get(f"{BACKEND_URL}/gold_standard?url={url}")
    
    if gs_resp.status_code == 200:
        gs_data = gs_resp.json()
        # 3. Se c'è il GS, chiediamo al backend di valutare le metriche
        eval_resp = requests.post(
            f"{BACKEND_URL}/evaluate", 
            json={"parsed_text": parse_data["parsed_text"], "gold_text": gs_data["gold_text"]}
        )
        if eval_resp.status_code == 200:
            metrics = eval_resp.json()["token_level_eval"]

    # Recupera di nuovo la lista URL per il menu
    domains = requests.get(f"{BACKEND_URL}/domains").json().get("domains", [])
    all_gs_urls = []
    for d in domains:
        gs_entries = requests.get(f"{BACKEND_URL}/full_gold_standard?domain={d}").json().get("gold_standard", [])
        all_gs_urls.extend([e["url"] for e in gs_entries])

    return templates.TemplateResponse("index.html", {
        "request": request,
        "gs_urls": all_gs_urls,
        "result": {
            "url": url,
            "title": parse_data.get("title"),
            "html_text": parse_data.get("html_text"),
            "parsed_text": parse_data.get("parsed_text"),
            "gold_text": gs_data.get("gold_text") if gs_data else None,
            "metrics": metrics
        }
    })