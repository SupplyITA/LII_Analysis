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
async def process_url(request: Request, url: str = Form(...), local: bool = Form(False)):
    
    try:
        domains = requests.get(f"{BACKEND_URL}/domains").json().get("domains", [])
        all_gs_urls = []
        for d in domains:
            gs_resp = requests.get(f"{BACKEND_URL}/full_gold_standard?domain={d}").json()
            for entry in gs_resp.get("gold_standard", []):
                all_gs_urls.append(entry["url"])
    except Exception:
        all_gs_urls = []

    # chiamata a parse (con nuovo schema)
    parse_resp = requests.post(f"{BACKEND_URL}/parse", json={"url": url, "local": local})
    
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
    # gs_resp = requests.get(f"{BACKEND_URL}/gold_standard?url={url}")
    judge_data = None

    # si controlla se l'url è già nel gs
    gs_check = requests.get(f"{BACKEND_URL}/gold_standard", params={"url": url})

    if gs_check.status_code == 200:
        gs_data = gs_check.json()

        # valutazione matematica
        eval_resp = requests.post(
            f"{BACKEND_URL}/evaluate", 
            json={"parsed_text": parse_data["parsed_text"], 
            "gold_text": gs_data["gold_text"]}
        )        
        if eval_resp.status_code == 200:
            metrics = eval_resp.json().get("token_level_eval")

        # valutazione llm judge
        j_resp = requests.post(
            f"{BACKEND_URL}/evaluate_judge", 
            json={"parsed_text": parse_data["parsed_text"], "gold_text": gs_data["gold_text"]}
        )
        if j_resp.status_code == 200:
            judge_data = j_resp.json()
         
    # invio al template
    return templates.TemplateResponse(request, "index.html", {
        "gs_urls": all_gs_urls,
        "result": {
            "url": url,
            "title": parse_data.get("title"),
            "html_text": parse_data.get("html_text"),
            "parsed_text": parse_data.get("parsed_text"),
            "gold_text": gs_data.get("gold_text") if gs_data else None,
            "metrics": metrics,
            "judge": judge_data
        },
        "error": None
    })