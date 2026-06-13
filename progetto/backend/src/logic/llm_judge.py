import httpx

OLLAMA_URL = "http://ollama:11434/api/generate"
MODEL_NAME = "llama3" 

async def evaluate_with_llm(parsed_text: str, gold_text: str) -> str:
    """
    Invia il testo estratto e il gold standard a Ollama per un giudizio qualitativo.
    """
    prompt = f"""Sei un 'LLM Judge', un esperto revisore di NLP (Natural Language Processing).
Il tuo compito è giudicare la qualità di un testo estratto in automatico da una pagina web, confrontandolo con il suo testo di riferimento ideale (Gold Standard).

--- TESTO ESTRATTO DAL PARSER ---
{parsed_text[:2000]} 

--- TESTO DI RIFERIMENTO (GOLD STANDARD) ---
{gold_text[:2000]}

Per favore, fornisci una breve valutazione qualitativa in italiano strutturata in questo modo:
1. Analisi dei difetti: Segnala se nel testo estratto manca del contenuto importante o se c'è rumore (come menu, banner o pubblicità).
2. Leggibilità: Valuta quanto il testo estratto sia pulito e scorrevole.
3. Voto Finale: Assegna un punteggio da 1 a 10.

Sii conciso e diretto.
"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False 
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(OLLAMA_URL, json=payload, timeout=120.0)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "Errore: Nessuna risposta testuale trovata.")
        
        except httpx.RequestError as e:
            return f"Errore di connessione a Ollama: Assicurati che il container sia acceso e il modello '{MODEL_NAME}' sia stato scaricato. (Dettaglio: {str(e)})"