"""Optional NPU interface; intentionally reports unavailable until runtime execution is verified."""
from hardware.hardware_detector import detect_hardware

def npu_status():
    hw=detect_hardware()
    return {"available":hw["npu_available"],"verified":False,"providers":hw["npu_providers"],"details":hw["npu_reason"]}
