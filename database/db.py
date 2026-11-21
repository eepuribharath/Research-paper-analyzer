"""SQLite persistence layer with foreign keys enabled on every connection."""
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from config import DB_PATH

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

class Database:
    def __init__(self, path: Path | str = DB_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self):
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize(self):
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        with self.connect() as conn:
            conn.executescript(schema)

    def list_papers(self):
        with self.connect() as c:
            return [dict(r) for r in c.execute("SELECT * FROM papers ORDER BY upload_date DESC")]

    def get_paper(self, paper_id):
        with self.connect() as c:
            row = c.execute("SELECT * FROM papers WHERE paper_id=?", (paper_id,)).fetchone()
            return dict(row) if row else None

    def get_by_hash(self, file_hash):
        with self.connect() as c:
            row = c.execute("SELECT * FROM papers WHERE file_hash=?", (file_hash,)).fetchone()
            return dict(row) if row else None

    def add_paper(self, metadata):
        paper_id = metadata.get("paper_id") or str(uuid.uuid4())
        values = (paper_id, metadata["filename"], metadata["file_hash"], metadata["title"],
                  metadata.get("authors", ""), metadata.get("abstract", ""), metadata.get("publication_year"),
                  metadata.get("total_pages", 0), now_iso(), metadata.get("processing_status", "processing"))
        with self.connect() as c:
            c.execute("""INSERT INTO papers(paper_id,filename,file_hash,title,authors,abstract,publication_year,total_pages,upload_date,processing_status)
                         VALUES(?,?,?,?,?,?,?,?,?,?)""", values)
        return paper_id

    def set_status(self, paper_id, status, error=""):
        with self.connect() as c:
            c.execute("UPDATE papers SET processing_status=?,error_message=? WHERE paper_id=?", (status,error,paper_id))

    def replace_chunks(self, paper_id, chunks):
        with self.connect() as c:
            c.execute("DELETE FROM paper_chunks WHERE paper_id=?", (paper_id,))
            c.executemany("INSERT INTO paper_chunks(chunk_id,paper_id,page_number,section_name,chunk_text,chunk_index) VALUES(?,?,?,?,?,?)",
                [(x["chunk_id"],paper_id,x["page_number"],x.get("section_name", ""),x["text"],x["chunk_index"]) for x in chunks])

    def list_chunks(self, paper_id=None):
        query = "SELECT c.*,c.chunk_text AS text,p.title FROM paper_chunks c JOIN papers p USING(paper_id)"
        args = ()
        if paper_id:
            query += " WHERE c.paper_id=?"; args = (paper_id,)
        query += " ORDER BY c.paper_id,c.chunk_index"
        with self.connect() as c:
            return [dict(r) for r in c.execute(query, args)]

    def save_summary(self, paper_id, kind, summary):
        with self.connect() as c:
            c.execute("INSERT INTO summaries(paper_id,summary_type,summary_text,created_at) VALUES(?,?,?,?)", (paper_id,kind,summary,now_iso()))

    def summaries_for(self, paper_id):
        with self.connect() as c:
            return [dict(r) for r in c.execute("SELECT * FROM summaries WHERE paper_id=? ORDER BY created_at DESC", (paper_id,))]

    def save_keywords(self, paper_id, keywords):
        with self.connect() as c:
            c.execute("DELETE FROM keywords WHERE paper_id=?", (paper_id,))
            c.executemany("INSERT INTO keywords(paper_id,keyword,score) VALUES(?,?,?)", [(paper_id,k,float(s)) for k,s in keywords])

    def keywords_for(self, paper_id=None):
        query = "SELECT * FROM keywords"; args=()
        if paper_id: query += " WHERE paper_id=?"; args=(paper_id,)
        with self.connect() as c: return [dict(r) for r in c.execute(query,args)]

    def record_search(self, query, count):
        with self.connect() as c: c.execute("INSERT INTO search_history(query,results_count,created_at) VALUES(?,?,?)", (query,count,now_iso()))

    def record_analysis(self, paper_id, kind, result):
        with self.connect() as c: c.execute("INSERT INTO analysis_history(paper_id,analysis_type,analysis_result,created_at) VALUES(?,?,?,?)", (paper_id,kind,json.dumps(result,ensure_ascii=False),now_iso()))

    def delete_paper(self, paper_id):
        with self.connect() as c: c.execute("DELETE FROM papers WHERE paper_id=?", (paper_id,))

    def counts(self):
        with self.connect() as c:
            return {name: c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for name,table in (("papers","papers"),("chunks","paper_chunks"),("pages","papers"))}
