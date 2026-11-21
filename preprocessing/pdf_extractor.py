"""Safe text-based PDF extraction using PyMuPDF."""
from pathlib import Path
import pymupdf as fitz

class PDFExtractionError(ValueError): pass

def extract_pdf(path: str | Path) -> dict:
    try:
        doc = fitz.open(path)
        if not doc.is_pdf or doc.page_count < 1:
            raise PDFExtractionError("The file is not a valid PDF or has no pages.")
        pages=[]
        for i,page in enumerate(doc):
            text=page.get_text("text", sort=True).strip()
            if text: pages.append({"page_number":i+1,"text":text})
        page_count=doc.page_count
        doc.close()
    except PDFExtractionError: raise
    except Exception as exc: raise PDFExtractionError(f"Could not read this PDF: {exc}") from exc
    full="\n\n".join(x["text"] for x in pages)
    if len(full.strip()) < 30:
        raise PDFExtractionError("No usable selectable text was found. This may be a scanned PDF; OCR is not included yet.")
    lines=[line.strip() for line in full.splitlines() if line.strip()]
    title=next((x for x in lines[:12] if 8 <= len(x) <= 240), Path(path).stem)
    abstract=""
    low=full.lower()
    start=low.find("abstract")
    if start>=0:
        candidate=full[start+8:].strip(" :\n\t")
        end=min([p for p in (candidate.lower().find("\n1. introduction"),candidate.lower().find("\nintroduction"),candidate.lower().find("\nkeywords")) if p>=0] or [1200])
        abstract=" ".join(candidate[:end].split())[:3000]
    years=__import__("re").findall(r"\b(?:19|20)\d{2}\b",full[:12000])
    authors=""
    return {"pages":pages,"total_pages":page_count,"full_text":full,"title":title,"abstract":abstract,
            "authors":authors,"publication_year":int(years[0]) if years else None}
