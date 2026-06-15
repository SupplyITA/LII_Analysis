from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
import requests
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# URL del backend 
BACKEND_URL = "http://backend:8003" 

# -------------------- Homepage
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    try:        
        status = requests.get(f"{BACKEND_URL}/status").json()
        domains = requests.get(f"{BACKEND_URL}/domains").json().get("domains", [])
    except Exception:
        status = {"backend": "error", "database": "error", "ollama": "error"}
        domains = []
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "status": status,
        "domains": domains
    })


# -------------------- Pagina di parser + evaluation
@app.get("/evaluation", response_class=HTMLResponse)
async def evaluation_page(request: Request):
    # url del gs per il menù a tendina
    all_urls = []
    try:
        domains = requests.get(f"{BACKEND_URL}/domains").json().get("domains", [])
        for d in domains:
            resp = requests.get(f"{BACKEND_URL}/gold_standard_urls", params={"domain": d}).json()
            all_urls.extend(resp.get("gold_standard_urls", []))
    except Exception: pass

    return templates.TemplateResponse("evaluation.html", {"request": request, "gs_urls": all_urls, "result": None})


@app.post("/evaluation", response_class=HTMLResponse)
async def evaluate_parser(request: Request, url: str = Form(...), local: bool = Form(False)):
    try:
        # parsing
        parse_resp = requests.post(f"{BACKEND_URL}/parse", json={"url": url, "local": local})
        if parse_resp.status_code != 200:
            raise Exception(parse_resp.json().get("detail", "Errore Parsing"))
        parse_data = parse_resp.json()

        # si controlla se esiste il gold standard
        gs_data = None
        metrics = None
        judge = None
        gs_resp = requests.get(f"{BACKEND_URL}/gold_standard", params={"url":url})

        if gs_resp.status_code == 200:
            gs_data = gs_resp.json()

            # valutazione matematica
            eval_resp = requests.post(f"{BACKEND_URL}/evaluate", json={
                "parsed_text": parse_data["parsed_text"],
                "gold_text": gs_data["gold_text"]
            })
            metrics = eval_resp.json().get("token_level_eval") if eval_resp.status_code == 200 else None

            # valutazione judge
            judge_resp = requests.post(f"{BACKEND_URL}/evaluate_judge", json={
                "parsed_text": parse_data["parsed_text"],
                "gold_text": gs_data["gold_text"]
            })
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
    except Exception as e:
            return templates.TemplateResponse("evaluation.html", {"request": request, "error": str(e), "gs_urls": []})
    
    return templates.TemplateResponse("evaluation.html", {"request": request, "result": result, "gs_urls": []})


# -------------------- Pagina gold standard builder
@app.post("/gs_builder/fetch_html")
async def fetch_html(url: str = Form(...)):
    """ Scarica l'HTML grezzo per il builder senza salvarlo """
    try:
        # Usiamo l'endpoint parse con l'URL, ma non salviamo nulla nel DB del backend
        resp = requests.post(f"{BACKEND_URL}/parse", json={"url": url, "local": False})
        if resp.status_code == 200:
            data = resp.json()
            return {"html_text": data.get("html_text", ""), "url": url}
        return {"error": "Impossibile scaricare l'HTML"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/gs_builder", response_class=HTMLResponse)
async def gs_builder_page(request: Request, domain: str = None):
    domains = requests.get(f"{BACKEND_URL}/domains").json().get("domains", [])
    urls_in_gs = []
    if domain:
        resp = requests.get(f"{BACKEND_URL}/gold_standard_urls", params={"domain": domain}).json()
        urls_in_gs = resp.get("gold_standard_urls", [])
    
    return templates.TemplateResponse("gs_builder.html", {
        "request": request, 
        "domains": domains, 
        "selected_domain": domain,
        "urls_in_gs": urls_in_gs
    })

@app.post("/gs_builder/add")
async def add_gs(url: str = Form(...), html_text: str = Form(...), gold_text: str = Form(...)):
    # aggiunge prima la web resource e poi il gs
    requests.post(f"{BACKEND_URL}/add_web_resource", json={"url": url, "html_text": html_text})
    requests.post(f"{BACKEND_URL}/add_gold_standard", json={"url": url, "gold_text": gold_text})
    return RedirectResponse(url="/gs_builder", status_code=303)


# -------------------- Pagina stats
@app.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request):
    try:
        stats = requests.get(f"{BACKEND_URL}/db_stats").json()
    except:
        stats = {}
    return templates.TemplateResponse("stats.html", {"request": request, "stats": stats})

# --------------------

'''
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Recupera i domini e gli URL del Gold Standard per il menu a tendina
    try:
        domains_resp = requests.get(f"{BACKEND_URL}/domains").json()
        domains = domains_resp.get("domains", [])
        
        all_gs_urls = []
        for d in domains:
            gs_resp = requests.get(f"{BACKEND_URL}/gold_standard_urls", params={"domain": d}).json()            
            for entry in gs_resp.get("gold_standard", []):
                all_gs_urls.append(url_in_list)
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
    '''