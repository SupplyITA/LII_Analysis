from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
<<<<<<< HEAD
from typing import List, Dict

# qui: importare le future funzioni per la logica del parser

app = FastAPI()
=======
>>>>>>> origin/pippo

# formato delle informazioni estratte dal parser
class ParseResponse(BaseModel):
    url: str
    domain: str
    title: str
    html_text: str
    parsed_text: str
<<<<<<< HEAD

# formato dati quantitativi
class TokenLevelEval(BaseModel):
    precision: float
    recall: float
    f1: float
    
# formato finale del json che verrà inviato al client
class EvaluationResponse(BaseModel):
    token_level_eval: TokenLevelEval

# input del POST
class EvaluateRequest(BaseModel):
    parsed_text : str
    gold_text: str


'''
○ GET /parse: esegue il parser per un documento di un dominio
○ GET /domains: restituisce la lista dei domini assegnati
○ GET /gold_standard: restituisce il gold standard per un documento 
○ GET /full_gold_standard: restituisce tutto il GS del dominio
○ POST /evaluate: dato risultato parsing e gs restituisce le metriche di evaluation
○ GET /full_gs_eval: restituisce l’evaluation aggregata su tutto il GS 
'''

@app.get("/parse", response_model = ParseResponse)
async def parse(url: str):
    # logica del parser (definita in un file a parte)
    pass

@app.get("/domains")
def get_domains():
    pass

@app.get("/gold_standard")
def get_gold_standard(domain: str):
    # logica per cercare il testo perfetto per il dominio
    pass

@app.get("/full_gold_standard")
def get_full_gold_standard(url:str):
    pass

@app.post("/evaluate", response_model = EvaluationResponse)
def evaluate(request: EvaluateRequest):
    # logiche per calcolare la precisione
    pass

@app.get("/full_gs_eval")
def full_gs_eval(domain: str):
    pass



=======
    
>>>>>>> origin/pippo
