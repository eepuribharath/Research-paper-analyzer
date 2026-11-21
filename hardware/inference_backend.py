from config import INFERENCE_DEVICE
from models.model_manager import resolve_device

def backend_status():
    try: device=resolve_device(); return {"requested":INFERENCE_DEVICE,"active":device,"verified":device=="cpu","message":"CPU inference selected and available."}
    except RuntimeError as exc: return {"requested":INFERENCE_DEVICE,"active":"unavailable","verified":False,"message":str(exc)}
