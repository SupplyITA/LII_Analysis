import json
import os

domains_path = os.path.join("..", "domains.json")
gs_dir = os.path.join("..", "gs_data")


# -- Logica di supporto per l'estrazione degli url --

''' Legge domains.json e restituisce la lista dei domini '''
def load_domains() -> list:
    with open(domains_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data["domains"]
    
''' Cerca un URL specifico nei file di gs_data '''
def find_url_in_gs(target_url: str) -> dict:
    domains = load_domains()

    for d in domains:
        filename = f"{d}_gs.json"
        path = os.path.join(gs_dir, filename)

        if os.path.exists(path):
            with open(path, "r", encoding= "utf-8") as f:
                gs_list = json.load(f)
                for entry in gs_list:
                    if entry["url"] == target_url:
                        return entry
    return None

''' Restituisce tutte le entry del gs per un dominio '''
def load_full_domain_gs(domain: str) -> list:
    path = os.path.join(gs_dir, f"{domain}_gs.json")

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None
