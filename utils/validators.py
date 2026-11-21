from config import MAX_UPLOAD_MB

def validate_upload(name, data):
    if not name.lower().endswith(".pdf"): raise ValueError("Only PDF files are supported.")
    if not data: raise ValueError("This file is empty.")
    if len(data)>MAX_UPLOAD_MB*1024*1024: raise ValueError(f"File exceeds the {MAX_UPLOAD_MB} MB upload limit.")
    if not data.startswith(b"%PDF-"): raise ValueError("The file does not have a valid PDF signature.")
