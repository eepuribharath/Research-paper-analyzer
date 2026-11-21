import hashlib
import re
from pathlib import Path

def sha256_bytes(data: bytes) -> str: return hashlib.sha256(data).hexdigest()

def safe_filename(name: str) -> str:
    base=Path(name).name
    base=re.sub(r"[^\w.() -]","_",base).strip(" .")
    return base[:160] or "paper.pdf"
