"""Paper-level summaries and metadata analysis."""
from models.summarization_model import summarize_text
from nlp.keyword_extractor import extract_keywords
import re

def summarize_paper(chunks):
    text="\n".join(c["text"] for c in chunks)
    try: return summarize_text(text)
    except Exception:
        # Keep a usable local baseline if model weights are not cached or memory is limited.
        sentences=text.replace("? ","?\n").replace(". ",".\n").splitlines()
        return " ".join(s.strip() for s in sentences[:8])[:2200]

def analyze_keywords(chunks): return extract_keywords([x["text"] for x in chunks])

SECTION_PATTERNS={
    "Introduction":r"(?:\b\d+(?:\.\d+)*\s+)?introduction\b",
    "Methodology":r"(?:\b\d+(?:\.\d+)*\s+)?(?:methodology|methods|materials\s+and\s+methods|proposed\s+approach)\b",
    "Results":r"(?:\b\d+(?:\.\d+)*\s+)?(?:results|experimental\s+results|evaluation)\b",
    "Conclusion":r"(?:\b\d+(?:\.\d+)*\s+)?(?:conclusion|conclusions|concluding\s+remarks)\b",
}

def summarize_sections(chunks, abstract=""):
    """Return labeled summaries; use full text where section headings are not found."""
    full="\n".join(c["text"] for c in chunks)
    matches=[]
    for name,pattern in SECTION_PATTERNS.items():
        for m in re.finditer(pattern,full,re.I): matches.append((m.start(),m.end(),name))
    matches.sort()
    detected={}
    for i,(start,end,name) in enumerate(matches):
        stop=matches[i+1][0] if i+1<len(matches) else len(full)
        body=full[end:stop].strip(" \n:.-")
        if len(body)>120 and name not in detected: detected[name]=body[:12000]
    result={}
    if abstract.strip(): result["Abstract"]={"text":_summary(abstract),"detected":True}
    else: result["Abstract"]={"text":"No abstract was reliably detected in the PDF text.","detected":False}
    for name in SECTION_PATTERNS:
        content=detected.get(name)
        result[name]={"text":_summary(content or full),"detected":bool(content)}
    result["Complete paper"]={"text":summarize_paper(chunks),"detected":True}
    return result

def _summary(text):
    if not text.strip(): return "No text was available for this section."
    try: return summarize_text(text)
    except Exception:
        return " ".join(text.replace("? ","?\n").replace(". ",".\n").splitlines()[:6])[:1400]
