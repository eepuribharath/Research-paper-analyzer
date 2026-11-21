PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS papers (
 paper_id TEXT PRIMARY KEY, filename TEXT NOT NULL, file_hash TEXT NOT NULL UNIQUE,
 title TEXT NOT NULL, authors TEXT NOT NULL DEFAULT '', abstract TEXT NOT NULL DEFAULT '',
 publication_year INTEGER, total_pages INTEGER NOT NULL DEFAULT 0,
 upload_date TEXT NOT NULL, processing_status TEXT NOT NULL DEFAULT 'processing',
 error_message TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS paper_chunks (
 chunk_id TEXT PRIMARY KEY, paper_id TEXT NOT NULL REFERENCES papers(paper_id) ON DELETE CASCADE,
 page_number INTEGER NOT NULL, section_name TEXT NOT NULL DEFAULT '', chunk_text TEXT NOT NULL,
 chunk_index INTEGER NOT NULL, UNIQUE(paper_id, chunk_index)
);
CREATE TABLE IF NOT EXISTS summaries (
 summary_id INTEGER PRIMARY KEY AUTOINCREMENT, paper_id TEXT NOT NULL REFERENCES papers(paper_id) ON DELETE CASCADE,
 summary_type TEXT NOT NULL, summary_text TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS keywords (
 keyword_id INTEGER PRIMARY KEY AUTOINCREMENT, paper_id TEXT NOT NULL REFERENCES papers(paper_id) ON DELETE CASCADE,
 keyword TEXT NOT NULL, score REAL NOT NULL, UNIQUE(paper_id, keyword)
);
CREATE TABLE IF NOT EXISTS search_history (
 search_id INTEGER PRIMARY KEY AUTOINCREMENT, query TEXT NOT NULL, results_count INTEGER NOT NULL,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS analysis_history (
 analysis_id INTEGER PRIMARY KEY AUTOINCREMENT, paper_id TEXT REFERENCES papers(paper_id) ON DELETE CASCADE,
 analysis_type TEXT NOT NULL, analysis_result TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunks_paper ON paper_chunks(paper_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_keywords_paper ON keywords(paper_id);
