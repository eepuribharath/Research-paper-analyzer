"""TF-IDF keyword extraction with a lightweight frequency fallback."""
import re
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer

def extract_keywords(texts, top_n=15):
    docs=[re.sub(r"\s+"," ",t).strip() for t in texts if t.strip()]
    if not docs: return []
    try:
        vec=TfidfVectorizer(stop_words="english",ngram_range=(1,2),max_features=3000,token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9-]{2,}\b")
        matrix=vec.fit_transform(docs); scores=matrix.sum(axis=0).A1
        items=sorted(zip(vec.get_feature_names_out(),scores),key=lambda x:x[1],reverse=True)
        return [(str(k),float(v)) for k,v in items[:top_n]]
    except ValueError:
        words=Counter(w.lower() for d in docs for w in re.findall(r"\b[a-zA-Z][a-zA-Z0-9-]{2,}\b",d))
        return [(k,float(v)) for k,v in words.most_common(top_n)]
