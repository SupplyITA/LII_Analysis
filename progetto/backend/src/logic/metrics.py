import re

def get_tokens(text: str) -> set:
    if not text:
        return set()
    return set(re.findall(r'\w+', text.lower()))

def compute_token_level_eval(parsed_text: str, gold_text: str) -> dict:
    extracted_tokens = get_tokens(parsed_text)
    gs_tokens = get_tokens(gold_text)

    num_extr = len(extracted_tokens)
    num_gs = len(gs_tokens)

    if num_extr == 0 and num_gs == 0:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    intr = extracted_tokens.intersection(gs_tokens)
    num_intr = len(intr)

    precision = num_intr / num_extr if num_extr > 0 else 0.0
    recall = num_intr / num_gs if num_gs > 0 else 0.0
    
    f1 = 0.0
    if (precision + recall) > 0:
        f1 = (2 * precision * recall) / (precision + recall)
    
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4)
    }