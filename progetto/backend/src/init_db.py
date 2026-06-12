import os
import json
from .database import engine, SessionLocal, Base
from .models import WebResource, GoldStandard

def init_db():
    print("Inizializzazione del database in corso...")
    
    #crea le tabelle nel database 
    Base.metadata.create_all(bind=engine)
    
    #popola il database con i dati in gs_data/
    db = SessionLocal()
    try:
        gs_dir = "/gs_data" 
        
        if not os.path.exists(gs_dir):
            print(f"ATTENZIONE: Cartella {gs_dir} non trovata.")
            return
        
        #cerca tutti i file JSON nella cartella
        for filename in os.listdir(gs_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(gs_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        print(f"Errore di lettura nel file {filename}")
                        continue
                    
                    for entry in data:
                        #controlla se l'URL è già presente per evitare duplicati
                        existing = db.query(WebResource).filter(WebResource.url == entry["url"]).first()
                        if not existing:
                            #inserisci nella tabella web_resources
                            web_res = WebResource(
                                url=entry["url"],
                                domain=entry["domain"],
                                title=entry["title"],
                                html_text=entry.get("html_text", "")
                            )
                            db.add(web_res)
                            
                            #inserisci nella tabella gold_standard
                            gold_std = GoldStandard(
                                url=entry["url"],
                                gold_text=entry.get("gold_text", "")
                            )
                            db.add(gold_std)
        
        #salva tutte le modifiche
        db.commit()
        print("Database popolato con successo con i Gold Standard!")
        
    except Exception as e:
        db.rollback()
        print(f"Errore durante il popolamento del DB: {e}")
    finally:
        db.close()