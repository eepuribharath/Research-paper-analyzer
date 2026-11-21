"""Evidence-based paper comparison and collection-level gap synthesis."""
FIELDS={"Objective":"objective|aim|purpose|we propose|this paper presents","Methodology":"method|approach|framework|algorithm|architecture","Datasets":"dataset|corpus|benchmark|data set","Metrics":"metric|accuracy|precision|recall|f1|rmse|auc","Results":"result|achieve|outperform|improv|performance","Limitations":"limitation|challenge|drawback|however|threats to validity","Future work":"future work|future research|further research|we plan"}

def extract_evidence(chunks, limit=2):
    import re
    out={}
    for field,terms in FIELDS.items():
        patt=re.compile(r"\b(?:"+terms+r")\b",re.I)
        found=[]
        for c in chunks:
            for s in re.split(r"(?<=[.!?])\s+",c["text"]):
                if patt.search(s): found.append({"text":s.strip(),"title":c.get("title",""),"page_number":c["page_number"],"paper_id":c["paper_id"]})
                if len(found)>=limit: break
            if len(found)>=limit: break
        out[field]=found
    return out

def compare_papers(chunks_a,chunks_b):
    return {"paper_a":extract_evidence(chunks_a),"paper_b":extract_evidence(chunks_b)}
