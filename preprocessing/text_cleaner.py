import re

def clean_text(text: str) -> str:
    text=text.replace("\u00ad","").replace("\x00", " ")
    text=re.sub(r"(?<=\w)-\s*\n\s*(?=\w)","",text)
    text=re.sub(r"[^\S\n]+"," ",text)
    text=re.sub(r"\n{3,}","\n\n",text)
    return text.strip()

def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])|\n+", text) if s.strip()]
