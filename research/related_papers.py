from models.embedding_model import encode_texts
import numpy as np

def related_papers(paper_id, papers, chunks, top_k=5):
    target=[c for c in chunks if c["paper_id"]==paper_id]
    if not target: return []
    others={p["paper_id"]:p for p in papers if p["paper_id"]!=paper_id}
    if not others: return []
    tvec=encode_texts([target[0]["text"]])[0]
    results=[]
    for pid,paper in others.items():
        group=[c["text"] for c in chunks if c["paper_id"]==pid]
        if not group: continue
        vec=encode_texts(group[:20]); sim=float(np.max(vec @ tvec))
        results.append({"paper":paper,"score":sim,"concepts":group[0][:240]})
    return sorted(results,key=lambda x:x["score"],reverse=True)[:top_k]
