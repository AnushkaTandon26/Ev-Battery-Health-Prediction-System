"""Diagnostic fact extraction.

Converts validated telemetry, the prediction result, recent history and the
existing maintenance plan into a single canonical ``DiagnosticFacts`` object.
Every downstream stage reads from this object instead of touching raw request
data, so report statements are always traceable to a labelled fact.

Facts are explicitly tagged by source: measured, predicted, derived or
historical (TRD "facts vs interpretation" boundary; PRD FR-01/FR-03).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

from .config import UNITS, LABELS, THRESHOLDS


@dataclass
class Measurement:
    """A single labelled measurement/prediction value."""
    parameter: str          # canonical key, e.g. "temperature"
    label: str
    value: Optional[float]
    unit: str
    source: str             # measured | predicted | user_provided | derived

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TrendFact:
    """Summary of change across recent records (only when enough data)."""
    records_considered: int
    health_drop_pct: float
    first_health: Optional[float]
    last_health: Optional[float]


@dataclass
class DiagnosticFacts:
    """Canonical, typed source of truth for one report."""
    # raw numeric values (floats, already validated/finite); may be None
    voltage: Optional[float]
    current: Optional[float]
    soc: Optional[float]
    temperature: Optional[float]
    degradation_level: Optional[float]
    power: Optional[float]           # derived = voltage * current
    health_score: Optional[float]    # predicted (after degradation adjustment)
    status: str                      # Safe | Warning | Critical | Unknown
    model_mode: str                  # keras | fallback | unavailable | unknown
    model_error: Optional[str]
    record_id: Optional[int]
    measurements: List[Measurement]
    existing_recommendations: List[str]
    maintenance_plan: Optional[Dict[str, Any]]
    trend: Optional[TrendFact]
    missing_fields: List[str]

    def measurement_map(self) -> Dict[str, Measurement]:
        return {m.parameter: m for m in self.measurements}


def _model_mode(prediction: Dict[str, Any]) -> str:
    """Translate the predictor metadata into a schema model_status value."""
    if prediction.get("model_active"):
        return "keras"
    if prediction.get("model_error"):
        # Model path attempted but failed/unavailable -> fallback heuristic used.
        return "fallback"
    # No model active, no error reported: fallback heuristic was used silently.
    return "fallback"


def _recent_health_drop(recent_records):
    """Mirror of agentic_ai._recent_health_drop, but returns context too."""
    if not recent_records:
        return None
    latest = recent_records[-THRESHOLDS["trend"]["min_records"] - 3:]  # a few points
    valid = [r for r in latest if r.get("health_score") is not None]
    if len(valid) < THRESHOLDS["trend"]["min_records"]:
        return None
    first = float(valid[0]["health_score"])
    last = float(valid[-1]["health_score"])
    drop = max(0.0, first - last)
    return TrendFact(
        records_considered=len(valid),
        health_drop_pct=round(drop, 2),
        first_health=round(first, 2),
        last_health=round(last, 2),
    )


def build_facts(
    telemetry: Dict[str, Any],
    prediction: Dict[str, Any],
    *,
    record_id: Optional[int] = None,
    recent_records: Optional[List[Dict[str, Any]]] = None,
    maintenance_plan: Optional[Dict[str, Any]] = None,
) -> DiagnosticFacts:
    """Assemble a DiagnosticFacts object from validated inputs.

    ``telemetry`` is the normalized dict from validation.validate_telemetry
    (keys: voltage, current, soc, temp/temperature, degradation_level).
    ``prediction`` is the dict returned by backend.utils.predict_battery_health.
    """
    recent_records = recent_records or []

    voltage = telemetry.get("voltage")
    current = telemetry.get("current")
    soc = telemetry.get("soc")
    temperature = telemetry.get("temperature", telemetry.get("temp"))
    degradation = telemetry.get("degradation_level")

    power = None
    if voltage is not None and current is not None:
        power = round(voltage * current, 2)

    health_score = prediction.get("health_score")
    status = prediction.get("status", "Unknown")

    measurements: List[Measurement] = []

    def add(param, value, source):
        if value is None:
            return
        measurements.append(Measurement(
            parameter=param, label=LABELS[param],
            value=round(float(value), 2), unit=UNITS[param], source=source,
        ))

    add("voltage", voltage, "measured")
    add("current", current, "measured")
    add("soc", soc, "measured")
    add("temperature", temperature, "measured")
    add("degradation_level", degradation, "user_provided")
    add("power", power, "derived")
    add("health_score", health_score, "predicted")

    missing = [k for k, v in (
        ("voltage", voltage), ("current", current), ("soc", soc),
        ("temperature", temperature),
    ) if v is None]
    if degradation is None:
        missing.append("degradation_level")

    trend = _recent_health_drop(recent_records)

    return DiagnosticFacts(
        voltage=voltage, current=current, soc=soc, temperature=temperature,
        degradation_level=degradation, power=power, health_score=health_score,
        status=status, model_mode=_model_mode(prediction),
        model_error=prediction.get("model_error"), record_id=record_id,
        measurements=measurements,
        existing_recommendations=list(prediction.get("recommendations", []) or []),
        maintenance_plan=maintenance_plan, trend=trend, missing_fields=missing,
    )
