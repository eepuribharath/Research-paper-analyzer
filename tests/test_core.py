import numpy as np
import pytest
import pymupdf as fitz
from database.db import Database
from preprocessing.pdf_extractor import extract_pdf, PDFExtractionError
from preprocessing.text_cleaner import clean_text
from preprocessing.text_chunker import chunk_pages
from retrieval.vector_store import VectorStore
from retrieval.rag_pipeline import answer_question

def make_pdf(path, text="ResearchLens studies semantic retrieval. This paper reports important evidence and useful methods."):
    doc=fitz.open(); page=doc.new_page(); page.insert_text((72,72),text); doc.save(path); doc.close()

def test_pdf_extraction_and_page_mapping(tmp_path):
    path=tmp_path/"study.pdf"; make_pdf(path)
    result=extract_pdf(path)
    assert result["total_pages"]==1 and "semantic retrieval" in result["full_text"]
    chunks=chunk_pages(result["pages"],target_tokens=8,overlap=2)
    assert chunks and all(c["page_number"]==1 for c in chunks)

def test_empty_scanned_and_corrupt_pdf(tmp_path):
    empty=tmp_path/"empty.pdf"; make_pdf(empty,"")
    with pytest.raises(PDFExtractionError): extract_pdf(empty)
    corrupt=tmp_path/"bad.pdf"; corrupt.write_bytes(b"not a pdf")
    with pytest.raises(PDFExtractionError): extract_pdf(corrupt)

def test_cleaner_and_sentence_aware_chunking():
    assert clean_text("inter-\nnational\tmethod") == "international method"
    chunks=chunk_pages([{"page_number":2,"text":"First sentence. Second sentence. Third sentence."}],target_tokens=4,overlap=1)
    assert len(chunks)>1 and chunks[0]["page_number"]==2

def test_database_cascade_and_duplicate_hash(tmp_path):
    db=Database(tmp_path/"t.sqlite3")
    pid=db.add_paper({"filename":"a.pdf","file_hash":"hash","title":"Paper","total_pages":1})
    with pytest.raises(Exception): db.add_paper({"filename":"b.pdf","file_hash":"hash","title":"Duplicate"})
    db.replace_chunks(pid,[{"chunk_id":"c1","page_number":1,"text":"hello","chunk_index":0}])
    assert db.list_chunks(pid)[0]["text"]=="hello"
    db.delete_paper(pid); assert not db.list_chunks()

def test_faiss_persistence_and_deletion(tmp_path):
    store=VectorStore(tmp_path); vectors=np.zeros((2,384),dtype="float32"); vectors[0,0]=1; vectors[1,1]=1
    store.add(["a","b"],vectors)
    assert store.search(vectors[0],1)[0]["chunk_id"]=="a"
    store=VectorStore(tmp_path); assert len(store.ids)==2
    store.remove(["a"]); assert store.ids==["b"]

def test_rag_insufficient_evidence_without_generation(monkeypatch):
    class Store:
        def search(self,*args,**kwargs): return []
    monkeypatch.setattr("retrieval.rag_pipeline.encode_texts",lambda texts: np.zeros((1,384),dtype="float32"))
    answer=answer_question("What happened?",[],Store())
    assert "not provide enough evidence" in answer["answer"] and answer["evidence"]==[]

def test_rag_citations_are_bound_to_retrieved_chunk_ids(monkeypatch):
    import retrieval.rag_pipeline as rag
    class Store:
        def search(self,*args,**kwargs): return [{"chunk_id":"known","score":0.8}]
    monkeypatch.setattr(rag,"encode_texts",lambda texts: np.zeros((1,384),dtype="float32"))
    monkeypatch.setattr(rag,"generate_text",lambda prompt:"Supported answer [1]. Invented citation [9].")
    source={"chunk_id":"known","paper_id":"p1","title":"Verified Paper","page_number":4,"text":"Evidence from the uploaded paper."}
    result=rag.answer_question("What evidence?",[source],Store())
    assert result["evidence"]==[{**source,"score":0.8}]
    assert "Verified Paper"==result["evidence"][0]["title"]
    assert "[1]" in result["answer"] and "[9]" not in result["answer"]

def test_section_summaries_label_heading_fallback(monkeypatch):
    import nlp.paper_analyzer as analyzer
    monkeypatch.setattr(analyzer,"summarize_text",lambda text:"local summary")
    long="This paper discusses the selected research evidence and describes motivation, scope, and context for the study. "
    sections=analyzer.summarize_sections([{"text":"Introduction "+long*2+"Methods "+long*2+"Results "+long*2+"Conclusion "+long*2}],"Short abstract.")
    assert sections["Introduction"]["detected"] is True
    assert sections["Methodology"]["detected"] is True
    assert sections["Abstract"]["detected"] is True
    assert sections["Results"]["text"]=="local summary"
