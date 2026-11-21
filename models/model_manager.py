"""Lazy, CPU-first model access. Models are never loaded as a side effect of import."""
from functools import lru_cache
import gc
import threading
from config import EMBEDDING_MODEL, SUMMARIZATION_MODEL, GENERATION_MODEL, INFERENCE_DEVICE
_active_model=None
_model_lock=threading.RLock()

def _prepare(kind):
    """Keep only one model family resident at a time for 8 GB machines."""
    global _active_model
    with _model_lock:
        if _active_model==kind: return
        if kind=="embedding": _pipeline.cache_clear()
        else: embedding_model.cache_clear()
        _pipeline.cache_clear()
        gc.collect()
        _active_model=kind

def resolve_device():
    # This build has no verified Ryzen AI execution provider integration.
    if INFERENCE_DEVICE == "npu":
        raise RuntimeError("NPU requested, but no compatible AMD Ryzen AI execution provider is configured. Use INFERENCE_DEVICE=cpu or auto.")
    return "cpu"

@lru_cache(maxsize=1)
def embedding_model():
    _prepare("embedding")
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL, device=resolve_device(), model_kwargs={"local_files_only":False})

@lru_cache(maxsize=1)
def _pipeline(task, model_id):
    from transformers import pipeline
    return pipeline(task, model=model_id, device=-1)

def embed(texts):
    return embedding_model().encode(texts, convert_to_numpy=True, normalize_embeddings=True, batch_size=8, show_progress_bar=False)

def summarize(text, max_length=180):
    _prepare("summarization")
    return _pipeline("summarization", SUMMARIZATION_MODEL)(text[:12000], max_length=max_length, min_length=40, do_sample=False, truncation=True)[0]["summary_text"]

def generate(prompt, max_new_tokens=220):
    _prepare("generation")
    return _pipeline("text2text-generation", GENERATION_MODEL)(prompt, max_new_tokens=max_new_tokens, do_sample=False, truncation=True)[0]["generated_text"]
