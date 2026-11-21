from models.embedding_model import encode_texts
from retrieval.vector_store import VectorStore

def search(query, chunks, store: VectorStore, top_k=5):
    if not query.strip(): return []
    hits=store.search(encode_texts([query])[0],top_k)
    by_id={x["chunk_id"]:x for x in chunks}
    return [{**by_id[h["chunk_id"]],"score":h["score"]} for h in hits if h["chunk_id"] in by_id]
