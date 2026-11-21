from models.model_manager import embed

def encode_texts(texts):
    if not texts: return []
    return embed(texts)
