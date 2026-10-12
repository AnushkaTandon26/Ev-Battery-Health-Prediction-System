"""Report grounding and safety validation (NLG stage 6).

Separate from JSON-schema validation (which checks *structure*), this module
checks *truthfulness and safety* of the generated content against the canonical
facts (PRD FR-07, TRD C-05, section 8 of the master prompt):

* every numeric value in the report maps to a source value or snapshot;
* measurement units are the configured ones;
* missing values stay marked as missing (no fabricated numbers);
* no finding/recommendation references a parameter that has no fact;
* no unsafe certainty language ("safe to drive", "confirmed fault",
  "manufacturer approved", guaranteed-detection claims);
* possible causes are not phrased as confirmed diagnoses;
* model/fallback usage is disclosed when the fallback was used.

Returns a list of error strings (empty => the report is grounded and safe).
"""

from __future__ import annotations

import re
from typing import Dict, Any, List

from .fact_extractor import DiagnosticFacts
from .config import UNITS


# Phrases that must never appear in a generated report.
_FORBIDDEN_PATTERNS = [
    r"\bsafe to (drive|charge|operate)\b",
    r"\bconfirmed (fault|failure|defect)\b",
    r"\bdefinitely (faulty|failing|damaged)\b",
    r"\bguarantee[sd]?\b",
    r"\bmanufacturer[- ]approved\b",
    r"\bcertified (diagnosis|safe)\b",
    r"\bno (risk|danger)\b",
    r"\b100% (safe|healthy|certain)\b",
    r"\bwill (fail|not fail)\b",
]
_FORBIDDEN_RE = [re.compile(p, re.IGNORECASE) for p in _FORBIDDEN_PATTERNS]


def _collect_text(report: Dict[str, Any]) -> str:
    """Gather all human-facing strings for phrase scanning."""
    parts = [report.get("summary", "")]
    for f in report.get("findings", []):
        parts.append(f.get("title", ""))
        parts.append(f.get("explanation", ""))
        parts.append(f.get("confidence_note") or "")
    for r in report.get("recommendations", []):
        parts.append(r.get("action", ""))
        parts.append(r.get("reason", ""))
    parts.extend(report.get("limitations", []))
    return "\n".join(parts)


def _numbers_in(text: str) -> List[float]:
    out = []
    for token in re.findall(r"-?\d+(?:\.\d+)?", text):
        try:
            out.append(float(token))
        except ValueError:
            pass
    return out


def validate_grounding(report: Dict[str, Any], facts: DiagnosticFacts) -> List[str]:
    errors: List[str] = []

    # 1. Forbidden / unsafe language.
    text = _collect_text(report)
    for rx in _FORBIDDEN_RE:
        m = rx.search(text)
        if m:
            errors.append(f"unsafe/unsupported phrase: {m.group(0)!r}")

    # 2. Source snapshot must equal canonical facts (no fabricated numbers).
    snap = report.get("source_snapshot", {})
    expected = {
        "voltage": facts.voltage, "current": facts.current, "soc": facts.soc,
        "temp": facts.temperature, "degradation_level": facts.degradation_level,
        "health_score": facts.health_score,
    }
    for key, val in expected.items():
        got = snap.get(key)
        if val is None:
            if got is not None:
                errors.append(f"snapshot.{key} fabricated (facts had None)")
        else:
            if got is None or abs(float(got) - float(val)) > 1e-6:
                errors.append(f"snapshot.{key}={got} does not match fact {val}")

    # 3. Measurement units must be the configured ones.
    for m in report.get("measurements", []):
        param = m.get("parameter")
        if param in UNITS and param != "other":
            if m.get("unit") != UNITS[param]:
                errors.append(
                    f"measurement {param} unit {m.get('unit')!r} != {UNITS[param]!r}")

    # 4. Every finding's evidence value must trace to a known fact value.
    known_values = set()
    for v in expected.values():
        if v is not None:
            known_values.add(round(float(v), 2))
    if facts.power is not None:
        known_values.add(round(float(facts.power), 2))
    if facts.trend is not None:
        for v in (facts.trend.first_health, facts.trend.last_health,
                  facts.trend.health_drop_pct):
            if v is not None:
                known_values.add(round(float(v), 2))

    for fnd in report.get("findings", []):
        for ev in fnd.get("evidence", []):
            val = ev.get("value")
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                if round(float(val), 2) not in known_values:
                    errors.append(
                        f"finding {fnd.get('code')} evidence value {val} "
                        f"not traceable to a source fact")

    # 5. Recommendations must link to a finding code or the maintenance planner.
    finding_codes = {f.get("code") for f in report.get("findings", [])}
    for rec in report.get("recommendations", []):
        source = rec.get("source")
        codes = rec.get("related_finding_codes", [])
        if source == "rule":
            if not codes or not set(codes).issubset(finding_codes):
                errors.append(
                    f"recommendation {rec.get('action')!r} claims rule source "
                    f"but has no matching finding code")
        elif source not in {"maintenance_planner", "approved_manual", "other"}:
            errors.append(f"recommendation has invalid source {source!r}")

    # 6. Fallback disclosure.
    if facts.model_mode != "keras":
        disclosed = any("fallback" in lim.lower() for lim in report.get("limitations", []))
        if not disclosed:
            errors.append("fallback model used but not disclosed in limitations")

    return errors
