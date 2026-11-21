"""Application configuration."""
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("RESEARCHLENS_DATA_DIR", BASE_DIR / "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
INDEX_DIR = DATA_DIR / "indexes"
DB_PATH = DATA_DIR / "researchlens.sqlite3"
MODEL_CACHE = Path(os.getenv("HF_HOME", DATA_DIR / "cache"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
INFERENCE_DEVICE = os.getenv("INFERENCE_DEVICE", "auto").lower()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
SUMMARIZATION_MODEL = os.getenv("SUMMARIZATION_MODEL", "sshleifer/distilbart-cnn-6-6")
GENERATION_MODEL = os.getenv("GENERATION_MODEL", "google/flan-t5-small")
CHUNK_TOKENS = 500
CHUNK_OVERLAP = 100
EMBEDDING_DIM = 384
for _directory in (DATA_DIR, UPLOAD_DIR, INDEX_DIR, MODEL_CACHE):
    _directory.mkdir(parents=True, exist_ok=True)
