from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import requests
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# URL del backend 
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

    return templates.TemplateResponse(request, "index.html", {
        "gs_urls": all_gs_urls,
        "result": None
    })

@app.post("/process", response_class=HTMLResponse)
async def process_url(request: Request, url: str = Form(...)):
    
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

    parse_resp = requests.get(f"{BACKEND_URL}/parse?url={url}")
    if parse_resp.status_code != 200:
        error_data = parse_resp.json()
        error_message = error_data.get("detail", "Errore durante il parsing dell'URL.")
        return templates.TemplateResponse(request, "index.html", {
            "gs_urls": all_gs_urls,
            "result": None,
            "error": error_message
        })
    
    parse_data = parse_resp.json()
    gs_data = None
    metrics = None
    llm_judgment = None 

    gs_resp = requests.get(f"{BACKEND_URL}/gold_standard?url={url}")
    
    if gs_resp.status_code == 200:
        gs_data = gs_resp.json()
        eval_resp = requests.post(
            f"{BACKEND_URL}/evaluate", 
            json={"parsed_text": parse_data["parsed_text"], "gold_text": gs_data["gold_text"]}
        )
        if eval_resp.status_code == 200:
            metrics = eval_resp.json().get("token_level_eval")

        try:
            llm_resp = requests.post(
                f"{BACKEND_URL}/llm_eval",
                json={"url": url},
                timeout=130.0
            )
            if llm_resp.status_code == 200:
                llm_judgment = llm_resp.json().get("llm_judgment")
        except requests.exceptions.RequestException as e:
            llm_judgment = f"Errore di connessione all'LLM. Dettaglio: {str(e)}"

    # passiamo il giudizio dell'LLM al template HTML
    return templates.TemplateResponse(request, "index.html", {
        "gs_urls": all_gs_urls,
        "result": parse_data,
        "gs_text": gs_data["gold_text"] if gs_data else None,
        "metrics": metrics,
        "llm_judgment": llm_judgment
    })