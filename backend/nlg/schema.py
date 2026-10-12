"""Load and validate against the project's diagnostic_report JSON Schema.

The schema file ships in ``project-docs/diagnostic_report.schema.json``. For a
self-contained deployment we also keep a copy path lookup that works whether
the app runs from the repo root or the backend directory. If the ``jsonschema``
library is unavailable, a lightweight built-in checker enforces the required
keys and enums so validation still happens (TRD: validate before persistence).
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import List, Dict, Any

_THIS = os.path.dirname(os.path.abspath(__file__))

# Candidate locations for the schema (repo layouts differ).
_SCHEMA_CANDIDATES = [
    os.path.join(_THIS, "diagnostic_report.schema.json"),              # bundled copy
    os.path.join(_THIS, "..", "..", "..", "project-docs",
                 "diagnostic_report.schema.json"),                      # sibling docs
    os.path.join(_THIS, "..", "..", "project-docs",
                 "diagnostic_report.schema.json"),
]


@lru_cache(maxsize=1)
def load_schema() -> Dict[str, Any]:
    for path in _SCHEMA_CANDIDATES:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
    raise FileNotFoundError(
        "diagnostic_report.schema.json not found in expected locations.")


# Enum constraints we enforce in the fallback checker (mirrors the schema).
_ENUMS = {
    "generation_method": {"template_nlg", "advanced_nlg", "hybrid"},
    "model_status": {"keras", "fallback", "unavailable", "unknown"},
    "overall_status": {"Safe", "Warning", "Critical", "Unknown"},
}

_REQUIRED_TOP = [
    "schema_version", "report_id", "battery_record_id", "generated_at",
    "generation_method", "model_status", "overall_status", "summary",
    "measurements", "findings", "recommendations", "limitations",
    "source_snapshot",
]


def _fallback_validate(report: Dict[str, Any]) -> List[str]:
    """Minimal structural check used when jsonschema is not installed."""
    errors = []
    for key in _REQUIRED_TOP:
        if key not in report:
            errors.append(f"missing required key: {key}")
    for key, allowed in _ENUMS.items():
        if key in report and report[key] not in allowed:
            errors.append(f"{key}={report[key]!r} not in {sorted(allowed)}")
    if report.get("schema_version") not in (None, "1.0"):
        errors.append("schema_version must be '1.0'")
    for key in ("measurements", "findings", "recommendations", "limitations"):
        if key in report and not isinstance(report[key], list):
            errors.append(f"{key} must be an array")
    snap = report.get("source_snapshot")
    if not isinstance(snap, dict):
        errors.append("source_snapshot must be an object")
    else:
        for sk in ("voltage", "current", "soc", "temp", "degradation_level",
                   "health_score", "status"):
            if sk not in snap:
                errors.append(f"source_snapshot missing {sk}")
    # finding codes must match the pattern
    import re
    code_re = re.compile(r"^[A-Z0-9_]{2,100}$")
    for fnd in report.get("findings", []) or []:
        if not code_re.match(fnd.get("code", "")):
            errors.append(f"finding code invalid: {fnd.get('code')!r}")
        if not fnd.get("evidence"):
            errors.append(f"finding {fnd.get('code')} has no evidence")
    return errors


def validate_report(report: Dict[str, Any]) -> List[str]:
    """Validate ``report`` against the schema.

    Returns a list of error strings (empty => valid). Prefers the ``jsonschema``
    library (full Draft 2020-12 validation) and falls back to the built-in
    structural checker otherwise.
    """
    try:
        import jsonschema  # type: ignore
        from jsonschema import Draft202012Validator
    except Exception:
        return _fallback_validate(report)

    try:
        schema = load_schema()
    except FileNotFoundError:
        return _fallback_validate(report)

    # jsonschema 3.x may not have Draft202012Validator; degrade gracefully.
    try:
        validator_cls = Draft202012Validator
    except Exception:  # pragma: no cover
        return _fallback_validate(report)

    try:
        validator = validator_cls(schema)
        return [f"{'/'.join(str(p) for p in e.path)}: {e.message}"
                for e in validator.iter_errors(report)]
    except Exception:
        # Any incompatibility -> structural fallback rather than silent pass.
        return _fallback_validate(report)
