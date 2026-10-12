"""Report generator — orchestrates the facts-first NLG pipeline.

    validate -> build_facts -> rule evaluate -> plan -> realize -> validate

Produces a report object shaped to ``diagnostic_report.schema.json`` plus a
human-readable text. Report generation never raises into the caller's
prediction flow: on failure it returns a ``report_status='failed'`` envelope so
a saved prediction is preserved (TRD NFR-01 / error-handling table).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from . import config
from .fact_extractor import build_facts, DiagnosticFacts
from .diagnostic_rules import evaluate, detect_conflicts
from .report_planner import plan_report
from .sentence_realizer import realize
from .report_validator import validate_grounding
from .schema import validate_report


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _measurements_payload(facts: DiagnosticFacts) -> List[Dict[str, Any]]:
    out = []
    for m in facts.measurements:
        parameter = m.parameter
        if parameter == "power":
            parameter = "other"           # schema enum has no 'power'
        out.append({
            "parameter": parameter,
            "label": m.label,
            "value": m.value,
            "unit": m.unit,
            "source": m.source if m.source in
            {"measured", "predicted", "user_provided", "derived"} else "derived",
        })
    return out


def _source_snapshot(facts: DiagnosticFacts) -> Dict[str, Any]:
    return {
        "voltage": facts.voltage,
        "current": facts.current,
        "soc": facts.soc,
        "temp": facts.temperature,
        "degradation_level": facts.degradation_level,
        "health_score": facts.health_score,
        "status": facts.status if facts.status in
        {"Safe", "Warning", "Critical", "Unknown"} else "Unknown",
    }


def build_report_object(
    facts: DiagnosticFacts,
    *,
    method: str = "context_aware",
    report_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Build the schema-shaped report dict (without persistence)."""
    findings = evaluate(facts)
    conflicts = detect_conflicts(facts, findings)
    plan = plan_report(facts, findings, conflicts)
    realized = realize(plan, method=method)

    overall_status = facts.status if facts.status in {
        "Safe", "Warning", "Critical"} else "Unknown"

    report = {
        "schema_version": config.SCHEMA_VERSION,
        "report_id": report_id,
        "battery_record_id": facts.record_id if facts.record_id is not None else 0,
        "generated_at": _utc_now_iso(),
        "generation_method": "template_nlg",
        "model_status": facts.model_mode if facts.model_mode in {
            "keras", "fallback", "unavailable", "unknown"} else "unknown",
        "overall_status": overall_status,
        "summary": realized["summary"] or f"Battery status: {overall_status}.",
        "measurements": _measurements_payload(facts),
        "findings": [f.as_dict() for f in findings],
        "recommendations": plan.recommendations,
        "limitations": plan.limitations,
        "source_snapshot": _source_snapshot(facts),
    }
    # Attach non-schema extras used by the frontend / evaluation. The schema
    # has additionalProperties:false, so validation is run on a trimmed copy.
    report["_rendered_text"] = realized["rendered_text"]
    report["_sections"] = realized["sections"]
    report["_generator_version"] = config.GENERATOR_VERSION
    report["_rules_version"] = config.RULES_VERSION
    report["_generation_method_detail"] = method
    return report


def _schema_payload(report: Dict[str, Any]) -> Dict[str, Any]:
    """Strip internal underscore keys before schema validation / persistence."""
    return {k: v for k, v in report.items() if not k.startswith("_")}


def generate_report(
    telemetry: Dict[str, Any],
    prediction: Dict[str, Any],
    *,
    record_id: Optional[int] = None,
    recent_records: Optional[list] = None,
    maintenance_plan: Optional[Dict[str, Any]] = None,
    method: str = "context_aware",
    report_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Full pipeline. Returns an envelope:

        {
          "report_status": "generated" | "failed",
          "report": <schema dict with internal extras> | None,
          "schema_errors": [...],
          "grounding_errors": [...],
          "error": <str> | None,
        }
    """
    try:
        facts = build_facts(
            telemetry, prediction, record_id=record_id,
            recent_records=recent_records, maintenance_plan=maintenance_plan)

        report = build_report_object(facts, method=method, report_id=report_id)

        payload = _schema_payload(report)
        grounding_errors = validate_grounding(payload, facts)
        schema_errors = validate_report(payload)

        if schema_errors or grounding_errors:
            # Try once with the deterministic baseline realizer as a fallback.
            if method != "baseline":
                return generate_report(
                    telemetry, prediction, record_id=record_id,
                    recent_records=recent_records,
                    maintenance_plan=maintenance_plan, method="baseline",
                    report_id=report_id)
            return {
                "report_status": "failed", "report": None,
                "schema_errors": schema_errors,
                "grounding_errors": grounding_errors,
                "error": "report failed validation",
            }

        return {
            "report_status": "generated", "report": report,
            "schema_errors": [], "grounding_errors": [], "error": None,
        }
    except Exception as exc:  # never break the prediction flow
        return {
            "report_status": "failed", "report": None,
            "schema_errors": [], "grounding_errors": [],
            "error": f"{type(exc).__name__}: {exc}",
        }
