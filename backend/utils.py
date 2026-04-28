import logging

logger = logging.getLogger(__name__)

def validate_inputs(v, i, soc, temp, deg):
    if not (2.0 <= v <= 5.0):
        return False, "Voltage out of range [2.0, 5.0]"
    if not (-50.0 <= i <= 50.0):
        return False, "Current out of range [-50.0, 50.0]"
    if not (0.0 <= soc <= 100.0):
        return False, "SOC out of range [0.0, 100.0]"
    if not (-30.0 <= temp <= 80.0):
        return False, "Temperature out of range [-30.0, 80.0]"
    return True, None

def is_valid_telemetry(payload):
    req_fields = ['voltage', 'current', 'soc', 'temp', 'degradation']
    for f in req_fields:
        if f not in payload:
            return False, f"Missing required field: {f}"
    return validate_inputs(
        float(payload['voltage']),
        float(payload['current']),
        float(payload['soc']),
        float(payload['temp']),
        float(payload['degradation'])
    )
