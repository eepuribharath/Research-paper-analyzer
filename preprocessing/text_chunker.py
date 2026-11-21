import re
import uuid
from config import CHUNK_TOKENS, CHUNK_OVERLAP
from preprocessing.text_cleaner import clean_text, sentences

def _tokens(text): return re.findall(r"\w+|[^\w\s]", text)

def chunk_pages(pages, target_tokens=CHUNK_TOKENS, overlap=CHUNK_OVERLAP):
    """Create sentence-aware approximate token windows, retaining all contributing pages."""
    chunks=[]; pending=[]; count=0; idx=0; page_for=[]
    def flush():
        nonlocal pending,count,page_for,idx
        if pending:
            chunks.append({"chunk_id":str(uuid.uuid4()),"page_number":min(page_for or [1]),"page_end":max(page_for or [1]),"section_name":"",
                           "text":" ".join(pending),"chunk_index":idx})
            idx+=1
            tail=_tokens(" ".join(pending))[-overlap:] if overlap else []
            pending=[" ".join(tail)] if tail else []; count=len(tail); page_for=page_for[-1:] if tail else []
    for page in pages:
        for sentence in sentences(clean_text(page["text"])):
            tok=len(_tokens(sentence))
            if pending and count+tok>target_tokens: flush()
            if tok>target_tokens:
                flush()
                words=sentence.split()
                for j in range(0,len(words),max(1,target_tokens-overlap)):
                    part=" ".join(words[j:j+target_tokens])
                    if part: chunks.append({"chunk_id":str(uuid.uuid4()),"page_number":page["page_number"],"page_end":page["page_number"],"section_name":"","text":part,"chunk_index":idx}); idx+=1
            else:
                pending.append(sentence); count+=tok; page_for.append(page["page_number"])
    flush()
    return chunks
