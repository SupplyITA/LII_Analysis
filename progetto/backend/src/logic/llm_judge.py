import httpx
import json
from typing import Dict, Any

OLLAMA_URL = "http://ollama:11434/api/chat"
MODEL_NAME = "llama3.2:3b" 

async def evaluate_with_llm(parsed_text: str, gold_text: str) -> Dict[str, Any]:
    """
    Invia il testo estratto e il gold standard a Ollama per un giudizio qualitativo.
    """
    prompt = f"""Sei un 'LLM Judge', un esperto revisore di NLP (Natural Language Processing).
Giudica la qualità di un testo estratto in automatico da una pagina web, confrontandolo con il suo testo di riferimento ideale (Gold Standard).
--- TESTO ESTRATTO DAL PARSER ---
{parsed_text[:2000]} 

--- TESTO DI RIFERIMENTO (GOLD STANDARD) ---
{gold_text[:2000]}

Rispondi SOLO con un JSON nel seguente formato:

{{
 "score": <tra 1 e 5>,
 "feedback": <breve descrizione della qualità del testo>
}}

Sii conciso e diretto.
"""

    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],        
        "stream": False, 
        "format": "json"
    }

    async with httpx.AsyncClient() as client:
        try:
            # timeout
            response = await client.post(OLLAMA_URL, json=payload, timeout=120.0)
            response.raise_for_status()
            
            raw_content = response.json()["message"]["content"]
            return json.loads(raw_content)
        
        except Exception as e:
            # fallback: se llm sbaglia formato o c'è un errore restituisce 1
            return {
                "score": 1,
                "feedback": f"Errore nel processamento del giudizio (Fallback): {str(e)}"
            }
