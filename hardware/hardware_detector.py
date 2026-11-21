import platform

def detect_hardware():
    try:
        import onnxruntime as ort
        providers=ort.get_available_providers()
    except Exception:
        providers=[]
    npu_providers=[p for p in providers if "ryzenai" in p.lower() or "vitisai" in p.lower()]
    reason=("AMD ONNX provider detected, but model execution is not implemented or verified." if npu_providers else
            "No AMD Ryzen AI/Vitis AI ONNX execution provider is available; NPU inference is not verified.")
    return {"platform":platform.platform(),"processor":platform.processor() or "Unknown","cpu_available":True,
            "onnx_providers":providers,"npu_providers":npu_providers,"npu_available":bool(npu_providers),"npu_reason":reason}
