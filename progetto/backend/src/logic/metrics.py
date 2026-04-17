import re

# trasforma il testo in un insieme di token puliti
def get_tokens(text: str) -> set:
    clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
    return set(clean_text.split())

# calcola precision, recall, F1
def compute_token_level_eval(parsed_text: str, gold_text: str) -> dict:
    extracted_tokens = get_tokens(parsed_text)
    gs_tokens = get_tokens(gold_text)

    intr = extracted_tokens.intersection(gs_tokens)
    num_intr = len(intr)
    num_extr = len(extracted_tokens)
    num_gs = len(gs_tokens)

    precision = num_intr / num_extr if num_extr > 0 else 0.0
    recall = num_intr / num_gs if num_gs > 0 else 0.0
    f1 = 0.0
    if (precision + recall) > 0:
        f1 = (2 * precision * recall) / (precision + recall)
    
    return {
        "precision": round(precision, 5),
        "recall": round(recall, 5),
        "f1": round(f1, 5)
    }
