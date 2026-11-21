"""Evidence-first local RAG with deterministic citation validation."""
from models.embedding_model import encode_texts
from models.generation_model import generate_text

def answer_question(question, chunks, store, top_k=5, threshold=0.20):
    if not question.strip(): return {"answer":"Enter a question to search the uploaded papers.","evidence":[]}
    hits=store.search(encode_texts([question])[0],top_k)
    by_id={c["chunk_id"]:c for c in chunks}
    evidence=[{**by_id[h["chunk_id"]],"score":h["score"]} for h in hits if h["chunk_id"] in by_id]
    evidence=[e for e in evidence if e["score"]>=threshold]
    if not evidence:
        return {"answer":"The uploaded papers do not provide enough evidence to answer this question confidently.","evidence":[]}
    context="\n\n".join(f"[{i}] {e['title']} (page {e['page_number']}): {e['text'][:1800]}" for i,e in enumerate(evidence,1))
    prompt=("Answer only from the supplied research excerpts. If unsupported, say so. Do not invent citations. "
            "Cite evidence using [1], [2] labels.\n\nEXCERPTS:\n"+context+"\n\nQUESTION: "+question+"\nANSWER:")
    try: answer=generate_text(prompt)
    except Exception as exc:
        # A concise extractive fallback remains grounded and keeps CPU workflow useful.
        answer="The local generation model is unavailable. The closest retrieved evidence is: " + evidence[0]["text"][:650].strip()+" [1]."
    # Only labels for evidence actually supplied are valid; remove hallucinated labels.
    import re
    valid={str(i) for i in range(1,len(evidence)+1)}
    answer=re.sub(r"\[(\d+)\]",lambda m:m.group(0) if m.group(1) in valid else "",answer).strip()
    return {"answer":answer,"evidence":evidence}
