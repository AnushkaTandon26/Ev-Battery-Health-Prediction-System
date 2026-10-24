"""
Input validation and normalization for battery telemetry and prediction facts.
Enforces FR-01 and FR-02: rejects non-numeric, non-finite, or out-of-domain telemetry.
"""
import math
from typing import Dict, Any, Tuple, Optional

# Reasonable physical bounds for EV pack telemetry
VALID_RANGES = {
    "voltage": (100.0, 1000.0),
    "current": (-600.0, 600.0),
    "soc": (0.0, 100.0),
    "temp": (-40.0, 120.0),
    "degradation_level": (0.0, 100.0),
}


class ValidationError(ValueError):
    """Raised when telemetry or prediction payload violates input contracts."""
    pass


def validate_and_normalize_inputs(
    telemetry: Dict[str, Any],
    prediction: Optional[Dict[str, Any]] = None
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """
    Validate telemetry inputs and prediction dictionary.
    Returns normalized (clean_telemetry, clean_prediction).
    Raises ValidationError if any value is invalid.
    """
    if not isinstance(telemetry, dict):
        raise ValidationError("Telemetry payload must be a dictionary.")

    clean_telemetry: Dict[str, float] = {}
    for key, (min_val, max_val) in VALID_RANGES.items():
        if key not in telemetry:
            if key == "degradation_level":
                raw_val = 0.0
            else:
                raise ValidationError(f"Missing required telemetry parameter: '{key}'")
        else:
            raw_val = telemetry[key]

        try:
            val = float(raw_val)
        except (ValueError, TypeError):
            raise ValidationError(f"Parameter '{key}' must be a numeric value, got '{raw_val}'")

        if math.isnan(val) or math.isinf(val):
            raise ValidationError(f"Parameter '{key}' has non-finite value: {val}")

        if val < min_val or val > max_val:
            raise ValidationError(
                f"Parameter '{key}' value {val} is outside valid domain [{min_val}, {max_val}]"
            )

        clean_telemetry[key] = round(val, 2)

    clean_prediction = prediction or {}
    if not isinstance(clean_prediction, dict):
        raise ValidationError("Prediction payload must be a dictionary.")

    # Validate health_score and status if provided
    if "health_score" in clean_prediction:
        try:
            hs = float(clean_prediction["health_score"])
            if math.isnan(hs) or math.isinf(hs) or hs < 0 or hs > 100:
                raise ValidationError(f"Prediction health_score must be in range [0, 100], got {hs}")
            clean_prediction["health_score"] = round(hs, 2)
        except (ValueError, TypeError):
            raise ValidationError("Prediction health_score must be a valid number.")

    if "status" in clean_prediction and clean_prediction["status"] not in ("Safe", "Warning", "Critical"):
        clean_prediction["status"] = "Warning"

    return clean_telemetry, clean_prediction
