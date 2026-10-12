"""Input validation for the diagnostic report pipeline.

Kept deliberately separate from language generation (TRD C-01, PRD FR-02).
Validation never invents missing measurements; it reports what is missing or
invalid so the caller can return a clear 400/422 instead of silently
substituting defaults.

The functions here operate on plain dicts and raise/return structured results,
so they can be unit tested without Flask.
"""

from __future__ import annotations

import math
from .config import VALIDATION_RANGES


# Canonical error codes (BACKEND_SCHEMA.md section 8 / TRD 10).
ERR_MISSING = "MISSING_FIELD"
ERR_NOT_NUMERIC = "NOT_NUMERIC"
ERR_NOT_FINITE = "NOT_FINITE"
ERR_OUT_OF_RANGE = "OUT_OF_RANGE"


class ValidationError(Exception):
    """Raised when telemetry fails validation.

    ``errors`` is a list of {field, code, message} dicts suitable for a
    JSON error response.
    """

    def __init__(self, errors):
        self.errors = errors
        super().__init__("; ".join(e["message"] for e in errors))


# Fields the report pipeline understands. ``temp`` is the request key; it is
# normalized to ``temperature`` downstream.
_FIELD_ALIASES = {
    "temperature": "temp",
}


def _coerce_number(value):
    """Return a float or raise ValueError. Rejects bools and non-finite."""
    if isinstance(value, bool):  # bool is a subclass of int; reject explicitly
        raise ValueError("boolean is not a numeric measurement")
    if value is None:
        raise ValueError("value is None")
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            raise ValueError("empty string")
        value = float(stripped)  # may raise ValueError
    number = float(value)
    return number


def validate_telemetry(data, *, strict=True):
    """Validate a telemetry dict for report generation.

    Parameters
    ----------
    data : dict
        Raw input, e.g. ``{"voltage":400,"current":18,"soc":83,"temp":29,
        "degradation_level":20}``.
    strict : bool
        When True (new report contract), required fields that are absent raise
        a ValidationError. When False (legacy /api/predict compatibility), the
        caller may still apply its own defaults; we only validate the values
        that are present.

    Returns
    -------
    dict
        Normalized telemetry with finite floats and a ``degradation_level`` key
        that may be ``None``.

    Raises
    ------
    ValidationError
        If any present value is non-numeric / non-finite / out of range, or
        (strict only) a required field is missing.
    """
    if not isinstance(data, dict):
        raise ValidationError([
            {"field": None, "code": "BAD_REQUEST",
             "message": "Request body must be a JSON object."}
        ])

    errors = []
    normalized = {}

    for field, rule in VALIDATION_RANGES.items():
        request_key = _FIELD_ALIASES.get(field, field)
        present = request_key in data and data[request_key] is not None
        if not present:
            if rule["required"] and strict:
                errors.append({
                    "field": request_key, "code": ERR_MISSING,
                    "message": f"'{request_key}' is required and was not provided.",
                })
            else:
                # Optional/absent: record None for degradation, skip others.
                if field == "degradation_level":
                    normalized["degradation_level"] = None
            continue

        raw = data[request_key]
        try:
            number = _coerce_number(raw)
        except (ValueError, TypeError):
            errors.append({
                "field": request_key, "code": ERR_NOT_NUMERIC,
                "message": f"'{request_key}' must be a finite number (got {raw!r}).",
            })
            continue

        if not math.isfinite(number):
            errors.append({
                "field": request_key, "code": ERR_NOT_FINITE,
                "message": f"'{request_key}' must be finite, not NaN or infinity.",
            })
            continue

        lo, hi = rule["min"], rule["max"]
        if number < lo or number > hi:
            errors.append({
                "field": request_key, "code": ERR_OUT_OF_RANGE,
                "message": (f"'{request_key}' = {number} is outside the accepted "
                            f"range [{lo}, {hi}]."),
            })
            continue

        normalized[field] = number

    if errors:
        raise ValidationError(errors)

    normalized.setdefault("degradation_level", None)
    return normalized


def validate_prediction(prediction):
    """Validate that a prediction result dict is usable for a report.

    Returns a list of problem strings (empty if OK). Does not raise so the
    caller can decide whether to degrade gracefully.
    """
    problems = []
    if not isinstance(prediction, dict):
        return ["prediction result is not an object"]

    hs = prediction.get("health_score")
    if hs is None:
        problems.append("prediction is missing health_score")
    else:
        try:
            hsf = float(hs)
            if not math.isfinite(hsf):
                problems.append("health_score is not finite")
        except (TypeError, ValueError):
            problems.append("health_score is not numeric")

    status = prediction.get("status")
    if status not in {"Safe", "Warning", "Critical", "Unknown"}:
        problems.append(f"unexpected status {status!r}")

    return problems
