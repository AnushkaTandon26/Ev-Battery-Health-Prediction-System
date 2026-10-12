"""Deterministic diagnostic rule engine.

Each rule inspects the canonical :class:`DiagnosticFacts` and, when its
condition holds, emits a :class:`Finding`. A finding carries a stable code,
severity, plain-English explanation and one or more evidence items that each
point back to a source parameter/value/unit and the configured rule that
fired. This is what makes the generated report auditable (PRD FR-03/FR-07).

Rules observe and compare against *configured* thresholds. They never assert a
confirmed physical fault: a high temperature is reported as "above the
configured review threshold", not as "the battery is overheating".
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

from .config import THRESHOLDS, UNITS, RULES_VERSION
from .fact_extractor import DiagnosticFacts


@dataclass
class Evidence:
    parameter: str
    value: Any
    unit: str
    source: str                       # measured|predicted|historical|configured_rule|derived|user_provided
    rule_code: Optional[str] = None
    threshold_description: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Finding:
    code: str                         # ^[A-Z0-9_]{2,100}$
    title: str
    severity: str                     # info|low|medium|high|critical|unknown
    explanation: str
    evidence: List[Evidence]
    confidence_note: Optional[str] = None
    # internal ordering weight (higher = more important); not serialized
    weight: int = field(default=0)

    def as_dict(self) -> Dict[str, Any]:
        d = {
            "code": self.code,
            "title": self.title,
            "severity": self.severity,
            "explanation": self.explanation,
            "evidence": [e.as_dict() for e in self.evidence],
            "confidence_note": self.confidence_note,
        }
        return d


_SEVERITY_WEIGHT = {
    "critical": 100, "high": 70, "medium": 40, "low": 20, "info": 10,
    "unknown": 5,
}


def _ev(param, value, source="measured", rule_code=None, threshold=None):
    return Evidence(
        parameter=param, value=value, unit=UNITS.get(param, ""),
        source=source, rule_code=rule_code, threshold_description=threshold,
    )


def _finding(code, title, severity, explanation, evidence, note=None):
    return Finding(
        code=code, title=title, severity=severity, explanation=explanation,
        evidence=evidence, confidence_note=note,
        weight=_SEVERITY_WEIGHT.get(severity, 0),
    )


# ---------------------------------------------------------------------------
# Individual rules. Each takes DiagnosticFacts and returns a Finding or None.
# ---------------------------------------------------------------------------

def rule_temperature(f: DiagnosticFacts):
    t = f.temperature
    if t is None:
        return None
    th = THRESHOLDS["temperature"]
    if t >= th["critical_c"]:
        sev, band = "critical", f"at or above the configured critical threshold ({th['critical_c']} °C)"
    elif t >= th["high_c"]:
        sev, band = "high", f"at or above the configured high threshold ({th['high_c']} °C)"
    elif t >= th["review_c"]:
        sev, band = "medium", f"at or above the configured review threshold ({th['review_c']} °C)"
    else:
        return None
    return _finding(
        "TEMPERATURE_HIGH", "Elevated temperature", sev,
        f"The measured temperature of {t:g} °C is {band}. Elevated pack "
        f"temperature can accelerate wear and may warrant checking the cooling "
        f"path, but this reading alone does not confirm a thermal fault.",
        [_ev("temperature", t, "measured", "TEMP_HIGH_V1", band)],
        note="Temperature thresholds are project defaults and must be set from the pack's rated operating range.",
    )


def rule_low_soc(f: DiagnosticFacts):
    s = f.soc
    if s is None:
        return None
    th = THRESHOLDS["soc"]
    if s <= th["very_low_pct"]:
        sev, band = "high", f"at or below the configured very-low threshold ({th['very_low_pct']}%)"
    elif s <= th["low_pct"]:
        sev, band = "medium", f"at or below the configured low threshold ({th['low_pct']}%)"
    else:
        return None
    return _finding(
        "SOC_LOW", "Low state of charge", sev,
        f"The State of Charge (SOC, the remaining charge) is {s:g}%, which is "
        f"{band}. A low charge level may limit available range and is worth "
        f"topping up depending on the planned use.",
        [_ev("soc", s, "measured", "SOC_LOW_V1", band)],
    )


def rule_high_current(f: DiagnosticFacts):
    c = f.current
    if c is None:
        return None
    th = THRESHOLDS["current"]
    a = abs(c)
    if a >= th["high_abs_a"]:
        sev, band = "high", f"at or above the configured high threshold ({th['high_abs_a']} A)"
    elif a >= th["elevated_abs_a"]:
        sev, band = "medium", f"at or above the configured elevated threshold ({th['elevated_abs_a']} A)"
    else:
        return None
    direction = "discharge" if c < 0 else "charge/load"
    return _finding(
        "CURRENT_HIGH", "High current magnitude", sev,
        f"The absolute current is {a:g} A ({direction}), which is {band}. "
        f"Sustained high current increases stress; consider moderating the "
        f"charge/discharge rate.",
        [_ev("current", c, "measured", "CURRENT_HIGH_V1", band)],
    )


def rule_degradation(f: DiagnosticFacts):
    d = f.degradation_level
    if d is None:
        return None
    th = THRESHOLDS["degradation"]
    if d >= th["service_pct"]:
        sev, band = "high", f"at or above the configured service-review level ({th['service_pct']})"
    elif d >= th["high_pct"]:
        sev, band = "medium", f"at or above the configured high level ({th['high_pct']})"
    elif d >= th["review_pct"]:
        sev, band = "low", f"at or above the configured review level ({th['review_pct']})"
    else:
        return None
    return _finding(
        "DEGRADATION_ELEVATED", "Elevated degradation index", sev,
        f"The provided degradation index is {d:g}, which is {band}. This is a "
        f"supplied index value and is not interpreted here as a specific "
        f"percentage of capacity loss.",
        [_ev("degradation_level", d, "user_provided", "DEGRADATION_V1", band)],
        note="Degradation semantics are undefined by the current system; wording is intentionally neutral.",
    )


def rule_health_band(f: DiagnosticFacts):
    hs = f.health_score
    if hs is None:
        return None
    th = THRESHOLDS["health"]
    if hs < th["critical_pct"]:
        sev = "critical"
        msg = (f"The predicted health score is {hs:g}%, in the Critical band "
               f"(below {th['critical_pct']}%).")
    elif hs < th["warning_pct"]:
        sev = "high"
        msg = (f"The predicted health score is {hs:g}%, in the Warning band "
               f"(below {th['warning_pct']}%).")
    elif hs < th["low_pct"]:
        sev = "low"
        msg = (f"The predicted health score is {hs:g}%, which is within the "
               f"Safe band but below the {th['low_pct']}% comfort level.")
    else:
        return None
    src = "predicted" if f.model_mode == "keras" else "predicted"
    note = None
    if f.model_mode != "keras":
        note = ("This score came from the heuristic fallback, not the trained "
                "model, so it should be treated as indicative only.")
    return _finding(
        "HEALTH_SCORE_LOW", "Predicted health below comfort level", sev, msg,
        [_ev("health_score", hs, src, "HEALTH_BAND_V1",
             f"status bands <{th['critical_pct']} Critical / <{th['warning_pct']} Warning")],
        note=note,
    )


def rule_health_trend(f: DiagnosticFacts):
    tr = f.trend
    if tr is None:
        return None
    if tr.health_drop_pct < THRESHOLDS["trend"]["significant_drop_pct"]:
        return None
    return _finding(
        "HEALTH_DECLINING", "Declining predicted health", "medium",
        f"Across the last {tr.records_considered} records, the predicted "
        f"health score fell by {tr.health_drop_pct:g} points "
        f"(from {tr.first_health:g}% to {tr.last_health:g}%). A sustained "
        f"decline is worth monitoring.",
        [_ev("health_score", tr.last_health, "historical", "TREND_V1",
             f"drop >= {THRESHOLDS['trend']['significant_drop_pct']} points over recent records")],
    )


_RULES = [
    rule_health_band,
    rule_temperature,
    rule_low_soc,
    rule_high_current,
    rule_degradation,
    rule_health_trend,
]


def evaluate(facts: DiagnosticFacts) -> List[Finding]:
    """Run all rules and return findings sorted by severity weight (desc)."""
    findings = []
    for rule in _RULES:
        try:
            result = rule(facts)
        except Exception:  # a buggy rule must not crash the whole report
            result = None
        if result is not None:
            findings.append(result)
    findings.sort(key=lambda fnd: fnd.weight, reverse=True)
    return findings


def detect_conflicts(facts: DiagnosticFacts, findings: List[Finding]) -> List[str]:
    """Surface contradictory / insufficient-evidence situations.

    Returns a list of plain-English caveat strings (not hidden). Example: the
    predictor says Safe but a critical-severity finding fired.
    """
    caveats = []
    has_critical = any(f.severity == "critical" for f in findings)
    if facts.status == "Safe" and has_critical:
        caveats.append(
            "The overall predicted status is Safe, yet a critical observation "
            "was detected; the conflicting signals should be reviewed rather "
            "than assuming the pack is problem-free.")
    if facts.missing_fields:
        caveats.append(
            "Some inputs were missing (" + ", ".join(facts.missing_fields) +
            "), so parts of this assessment are incomplete.")
    return caveats
