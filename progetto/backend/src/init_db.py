import os
import json
import time
from sqlalchemy.exc import OperationalError
from .database import engine, SessionLocal, Base
from .models import WebResource, GoldStandard

def init_db():    
    for attempt in range(10):
        try:
            # crea le tabelle nel database
            Base.metadata.create_all(bind=engine)
            print("Connessione a MariaDB stabilita con successo!")
            break  # Se ci riesce, esce dal ciclo di attesa
        except OperationalError:
            print(f"MariaDB non è ancora pronto (tentativo {attempt+1}/10). Attendo 3 secondi...")
            time.sleep(3)
    else:
        print("Errore critico: Il database non ha risposto in tempo.")
        return
    # ------------------------------------------------------------------
    
    # popola il database con i dati in gs_data/
    db = SessionLocal()
    try:
        gs_dir = "/gs_data" 
        
        if not os.path.exists(gs_dir):
            print(f"ATTENZIONE: Cartella {gs_dir} non trovata.")
            return
        
        for filename in os.listdir(gs_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(gs_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        continue
                    
                    for entry in data:
                        existing = db.query(WebResource).filter(WebResource.url == entry["url"]).first()
                        if not existing:
                            web_res = WebResource(
                                url=entry["url"],
                                domain=entry["domain"],
                                title=entry["title"],
                                html_text=entry.get("html_text", "")
                            )
                            db.add(web_res)
                            
                            gold_std = GoldStandard(
                                url=entry["url"],
                                gold_text=entry.get("gold_text", "")
                            )
                            db.add(gold_std)
        db.commit()
        print("Database popolato con successo con i Gold Standard!")
        
    except Exception as e:
        db.rollback()
        print(f"Errore durante il popolamento del DB: {e}")
    finally:
        db.close()
