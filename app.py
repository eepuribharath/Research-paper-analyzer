"""ResearchLens: local research-paper analysis dashboard."""
import json
import logging
from pathlib import Path
import streamlit as st
import pandas as pd
try:
    import plotly.express as px
except ImportError:
    px=None
from config import UPLOAD_DIR, INDEX_DIR, DB_PATH, MODEL_CACHE, EMBEDDING_MODEL, SUMMARIZATION_MODEL, GENERATION_MODEL
from database.db import Database
from preprocessing.pdf_extractor import extract_pdf, PDFExtractionError
from preprocessing.text_chunker import chunk_pages
from preprocessing.text_cleaner import clean_text
from retrieval.vector_store import VectorStore
from retrieval.semantic_search import search
from retrieval.rag_pipeline import answer_question
from nlp.paper_analyzer import summarize_paper, summarize_sections, analyze_keywords
from nlp.comparison import compare_papers
from research.gap_analyzer import analyze_gaps
from research.related_papers import related_papers
from hardware.inference_backend import backend_status
from hardware.hardware_detector import detect_hardware
from utils.file_utils import sha256_bytes, safe_filename
from utils.validators import validate_upload
from utils.logging_config import logging

st.set_page_config(page_title="ResearchLens",page_icon="🔎",layout="wide",initial_sidebar_state="expanded")
st.markdown("""<style>
html,body,[class*="css"]{font-family:'Segoe UI',sans-serif} h1,h2,h3{font-family:'Segoe UI',sans-serif}
.hero{padding:1.2rem 0 .5rem}.muted{color:#708090}.citation{border-left:3px solid #28a897;padding:.7rem 1rem;background:#f3f8f7;border-radius:0 8px 8px 0;margin:.5rem 0}
div[data-testid="stMetric"]{background:#f7f9fb;padding:14px;border-radius:12px;border:1px solid #e8edf2}
</style>""",unsafe_allow_html=True)

@st.cache_resource
def get_db(): return Database()
@st.cache_resource
def get_store(): return VectorStore()
db=get_db(); store=get_store()
st.sidebar.markdown("# 🔎 ResearchLens")
st.sidebar.caption("Local research paper intelligence")
pages=["Research assistant","Dashboard","Upload papers","Paper analyzer","Paper comparison","Research gaps","Semantic search","Settings"]
if "workspace_page" not in st.session_state:
    requested=st.query_params.get("page", "")
    st.session_state.workspace_page="Research assistant" if requested in ("assistant","chat") else "Research assistant"
page=st.sidebar.radio("Workspace",pages,label_visibility="collapsed",key="workspace_page")
papers=db.list_papers(); chunks=db.list_chunks();

def process_pdf(name,data,reprocess_id=None):
    validate_upload(name,data)
    digest=sha256_bytes(data)
    duplicate=db.get_by_hash(digest)
    if duplicate and not reprocess_id: raise ValueError(f"Already uploaded as ‘{duplicate['title']}’.")
    safe=safe_filename(name); dest=UPLOAD_DIR/(digest[:12]+"_"+safe)
    dest.write_bytes(data)
    info=extract_pdf(dest)
    metadata={"filename":safe,"file_hash":digest,"title":info["title"],"authors":info["authors"],"abstract":info["abstract"],"publication_year":info["publication_year"],"total_pages":info["total_pages"]}
    paper_id=reprocess_id or db.add_paper(metadata)
    # Preserve a real vector-to-chunk relationship; do not mark complete if models fail.
    if reprocess_id:
        store.remove([x["chunk_id"] for x in db.list_chunks(paper_id)])
    new_chunks=chunk_pages(info["pages"])
    for c in new_chunks: c["text"]=clean_text(c["text"])
    db.replace_chunks(paper_id,new_chunks)
    db.set_status(paper_id,"embedding")
    try:
        from models.embedding_model import encode_texts
        import numpy as np
        vectors=encode_texts([c["text"] for c in new_chunks])
        store.add([c["chunk_id"] for c in new_chunks],np.asarray(vectors,dtype="float32"))
        db.set_status(paper_id,"ready")
    except Exception as exc:
        logging.exception("Embedding failed for %s",safe)
        db.set_status(paper_id,"needs_index",str(exc)[:500])
        raise RuntimeError("Text was extracted, but local embedding/indexing failed. Check model access/cache, then use Reprocess. Details: "+str(exc)) from exc
    return paper_id

def show_evidence(ev):
    for e in ev:
        title=e.get("title","Paper"); page=e.get("page_number","?"); score=e.get("score")
        st.markdown(f"<div class='citation'><b>{title}</b> · page {page}"+(f" · similarity {score:.3f}" if score is not None else "")+f"<br><br>{e['text']}</div>",unsafe_allow_html=True)

def paper_label(p): return p["title"]+f" · {p['paper_id'][:8]}"

if page=="Dashboard":
    st.markdown("<div class='hero'>",unsafe_allow_html=True); st.title("Research dashboard"); st.caption("A local workspace for reading, searching, and comparing your research collection."); st.markdown("</div>",unsafe_allow_html=True)
    counts=db.counts(); ready=sum(p["processing_status"]=="ready" for p in papers); pages_total=sum(p["total_pages"] for p in papers)
    a,b,c,d=st.columns(4); a.metric("Papers",len(papers)); b.metric("Pages",pages_total); c.metric("Text chunks",len(chunks)); d.metric("Indexed papers",ready)
    left,right=st.columns([1.3,1])
    with left:
        st.subheader("Collection")
        if papers:
            frame=pd.DataFrame([{"Paper":p["title"],"Pages":p["total_pages"],"Status":p["processing_status"],"Uploaded":p["upload_date"][:10]} for p in papers])
            st.dataframe(frame,use_container_width=True,hide_index=True)
            if px: st.plotly_chart(px.bar(frame,x="Paper",y="Pages",color="Status",title="Pages by paper"),use_container_width=True)
            else: st.bar_chart(frame.set_index("Paper")["Pages"])
        else: st.info("Upload a PDF to start building your collection.")
    with right:
        st.subheader("Local inference")
        backend=backend_status(); st.success(backend["message"] if backend["active"]=="cpu" else backend["message"])
        st.caption("Models load only when a feature first needs them. No document content is sent to a hosted AI service.")
        st.subheader("Recent uploads")
        for p in papers[:5]: st.write(f"**{p['title']}** · {p['processing_status']}")

elif page=="Upload papers":
    st.title("Upload papers"); st.write("PDF files are processed on this computer. Scanned documents without selectable text need OCR, which is not included yet.")
    uploads=st.file_uploader("Choose one or more research PDFs",type=["pdf"],accept_multiple_files=True,help="Maximum 50 MB per file by default.")
    if st.button("Process uploaded papers",type="primary",disabled=not uploads):
        progress=st.progress(0)
        for i,f in enumerate(uploads):
            try:
                with st.status(f"Extracting and indexing {f.name}…",expanded=False):
                    pid=process_pdf(f.name,f.getvalue()); st.toast(f"Added {db.get_paper(pid)['title']}")
            except Exception as exc: st.error(f"{f.name}: {exc}")
            progress.progress((i+1)/len(uploads))
        st.rerun()
    st.subheader("Your papers")
    for p in db.list_papers():
        with st.expander(f"{p['title']} · {p['processing_status']} · {p['total_pages']} pages"):
            st.write(f"**File:** {p['filename']} · **Year:** {p['publication_year'] or 'Not detected'}")
            if p["abstract"]: st.write(p["abstract"])
            if p["error_message"]: st.warning(p["error_message"])
            c1,c2=st.columns(2)
            if c1.button("Reprocess",key="reprocess"+p["paper_id"]):
                try:
                    dest=UPLOAD_DIR/(p["file_hash"][:12]+"_"+safe_filename(p["filename"]))
                    process_pdf(p["filename"],dest.read_bytes(),p["paper_id"]); st.success("Reprocessed"); st.rerun()
                except Exception as exc: st.error(str(exc))
            if c2.button("Delete paper",key="delete"+p["paper_id"]):
                ids=[x["chunk_id"] for x in db.list_chunks(p["paper_id"])]; store.remove(ids); db.delete_paper(p["paper_id"])
                (UPLOAD_DIR/(p["file_hash"][:12]+"_"+safe_filename(p["filename"]))).unlink(missing_ok=True)
                st.rerun()

elif page=="Paper analyzer":
    st.title("Paper analyzer")
    if not papers: st.info("Upload a paper first.")
    else:
        selected=st.selectbox("Choose a paper",papers,format_func=lambda p:p["title"]); p=db.get_paper(selected["paper_id"]); pc=db.list_chunks(p["paper_id"])
        m1,m2,m3=st.columns(3); m1.metric("Pages",p["total_pages"]); m2.metric("Chunks",len(pc)); m3.metric("Words",sum(len(c["text"].split()) for c in pc))
        st.subheader("Paper details"); st.write(f"**Authors:** {p['authors'] or 'Not detected'} · **Year:** {p['publication_year'] or 'Not detected'} · **Status:** {p['processing_status']}")
        if p["abstract"]: st.info(p["abstract"])
        x,y=st.columns(2)
        if x.button("Generate paper and section summaries",type="primary"):
            with st.spinner("Summarizing sections locally. First use downloads the selected model…"):
                summaries=summarize_sections(pc,p["abstract"])
                for kind,summary in summaries.items(): db.save_summary(p["paper_id"],kind,summary["text"])
                db.record_analysis(p["paper_id"],"summaries",summaries); st.session_state["summaries_"+p["paper_id"]]=summaries
        if y.button("Extract keywords"):
            kws=analyze_keywords(pc); db.save_keywords(p["paper_id"],kws); st.session_state["keywords_"+p["paper_id"]]=kws
        summaries=st.session_state.get("summaries_"+p["paper_id"])
        if summaries:
            st.subheader("Paper summaries")
            for section,summary in summaries.items():
                with st.expander(section+("" if summary["detected"] else " · section not detected; overall text used"),expanded=section=="Complete paper"):
                    st.write(summary["text"])
        kws=st.session_state.get("keywords_"+p["paper_id"],db.keywords_for(p["paper_id"]))
        if kws:
            st.subheader("Important terms")
            df=pd.DataFrame(kws,columns=["Keyword","Score"]) if kws and isinstance(kws[0],tuple) else pd.DataFrame([{"Keyword":k["keyword"],"Score":k["score"]} for k in kws])
            if px: st.plotly_chart(px.bar(df.head(12),x="Score",y="Keyword",orientation="h"),use_container_width=True)
            else: st.bar_chart(df.head(12).set_index("Keyword")["Score"])
        with st.expander("Extracted text chunks"):
            for c in pc[:30]: st.markdown(f"**Page {c['page_number']}** · {c['section_name'] or 'Text'}\n\n{c['text']}")
        st.subheader("Related papers in your collection")
        if len(papers)<2: st.caption("Add another paper to discover related work within this collection.")
        elif st.button("Find related papers",key="related_"+p["paper_id"]):
            try:
                for item in related_papers(p["paper_id"],papers,chunks):
                    st.markdown(f"**{item['paper']['title']}** · semantic similarity {item['score']:.3f}")
                    st.caption("Example passage from this paper: "+item["concepts"])
            except Exception as exc: st.error(f"Could not calculate related papers: {exc}")

elif page=="Research assistant":
    st.title("Research assistant"); st.caption("Answers use retrieved excerpts from your uploaded papers. Check the evidence below each response.")
    if "chat" not in st.session_state: st.session_state.chat=[]
    for item in st.session_state.chat:
        with st.chat_message(item["role"]): st.write(item["text"]); show_evidence(item.get("evidence",[]))
    q=st.chat_input("Ask a question about your papers…",disabled=not chunks)
    if q:
        st.session_state.chat.append({"role":"user","text":q})
        with st.chat_message("assistant"):
            with st.spinner("Searching papers and generating a grounded answer…"):
                result=answer_question(q,db.list_chunks(),store); st.write(result["answer"]); show_evidence(result["evidence"])
        st.session_state.chat.append({"role":"assistant","text":result["answer"],"evidence":result["evidence"]}); st.rerun()
    if st.button("Clear conversation"): st.session_state.chat=[]; st.rerun()

elif page=="Paper comparison":
    st.title("Paper comparison")
    if len(papers)<2: st.info("Upload at least two papers to compare.")
    else:
        p1=st.selectbox("First paper",papers,index=0,key="p1",format_func=lambda p:p["title"]); p2=st.selectbox("Second paper",papers,index=1,key="p2",format_func=lambda p:p["title"])
        if p1["paper_id"]==p2["paper_id"]: st.warning("Select two different papers.")
        elif st.button("Compare evidence",type="primary"):
            result=compare_papers(db.list_chunks(p1["paper_id"]),db.list_chunks(p2["paper_id"]))
            rows=[]
            for field in result["paper_a"]:
                def fmt(items): return "\n".join(f"{x['text']} (p. {x['page_number']})" for x in items) or "Not found in extracted text"
                rows.append({"Aspect":field,p1["title"]:fmt(result["paper_a"][field]),p2["title"]:fmt(result["paper_b"][field])})
            st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
            st.caption("Each statement is a text match from the extracted paper; absence means it was not reliably detected.")
            try:
                from models.generation_model import generate_text
                prompt="Compare only facts in the following extracted evidence. Say when a field is missing and label any inference. Do not add facts.\n"+json.dumps(result,ensure_ascii=False)[:7000]
                with st.spinner("Writing a concise evidence-based comparison…"): st.write(generate_text(prompt))
            except Exception: st.caption("Local generation model is unavailable; the structured evidence comparison above is still available.")

elif page=="Research gaps":
    st.title("Potential research opportunities"); st.warning("Potential research opportunities requiring further literature verification. This analysis cannot establish novelty beyond the papers you upload.")
    if not chunks: st.info("Upload and index papers first.")
    elif st.button("Analyze collection",type="primary"):
        result=analyze_gaps(chunks); db.record_analysis(None,"research_gaps",result)
        for gap in result["gaps"]:
            st.subheader(gap["opportunity"]); st.write(gap["why"]); st.markdown(f"**Possible research question:** {gap['research_question']}")
            show_evidence(gap["evidence"])
elif page=="Semantic search":
    st.title("Semantic search"); st.write("Search by meaning across indexed paper excerpts.")
    q=st.text_input("Research question or concept",placeholder="What limitations do the authors report?"); k=st.slider("Results",1,15,5)
    if st.button("Search collection",type="primary",disabled=not q or not chunks):
        try:
            results=search(q,chunks,store,k); db.record_search(q,len(results))
            if not results: st.info("No matching indexed excerpts were found.")
            for r in results: show_evidence([r])
        except Exception as exc: st.error(str(exc))

elif page=="Settings":
    st.title("Settings and model status"); b=backend_status(); hw=detect_hardware()
    a,c=st.columns(2); a.metric("Requested backend",b["requested"]); c.metric("Active backend",b["active"])
    st.info(b["message"]); st.write(f"**CPU:** {hw['processor']} · **NPU:** {'Provider detected, inference unverified' if hw['npu_available'] else 'Not verified'}")
    st.caption(hw["npu_reason"])
    st.caption("ONNX Runtime providers: "+(", ".join(hw.get("onnx_providers",[])) or "not available"))
    st.subheader("Local models")
    st.write(f"**Embeddings:** `{EMBEDDING_MODEL}` (384 dimensions)")
    st.write(f"**Summarization:** `{SUMMARIZATION_MODEL}`")
    st.write(f"**Generation:** `{GENERATION_MODEL}`")
    st.caption("Models are downloaded from Hugging Face on first use, then cached. Set HF_HUB_OFFLINE=1 to require cached models.")
    st.write(f"**Model cache:** `{MODEL_CACHE}` · **Database:** `{DB_PATH}` · **FAISS index:** `{INDEX_DIR}`")
    st.write(f"**FAISS vectors:** {len(store.ids)} · **Database chunks:** {len(chunks)}")
    if len(store.ids)!=len(chunks): st.warning("The index and database chunk counts differ. Reprocess the affected paper(s) to repair the index.")
