"""
Main Report Generator Pipeline.
Coordinates all stages of facts-first Natural Language Generation:
Validation -> Fact Extraction -> Rule Evaluation -> Content Planning -> Text Realization -> Report Validation.
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional

try:
    from backend.nlg.validation import validate_and_normalize_inputs, ValidationError
    from backend.nlg.fact_extractor import extract_diagnostic_facts
    from backend.nlg.diagnostic_rules import evaluate_diagnostic_rules
    from backend.nlg.report_planner import plan_report_content
    from backend.nlg.sentence_realizer import realize_sentences
    from backend.nlg.report_validator import validate_complete_report
    from backend.nlg.config import SYSTEM_LIMITATIONS
except ImportError:
    from nlg.validation import validate_and_normalize_inputs, ValidationError
    from nlg.fact_extractor import extract_diagnostic_facts
    from nlg.diagnostic_rules import evaluate_diagnostic_rules
    from nlg.report_planner import plan_report_content
    from nlg.sentence_realizer import realize_sentences
    from nlg.report_validator import validate_complete_report
    from nlg.config import SYSTEM_LIMITATIONS


def generate_diagnostic_report(
    telemetry: Dict[str, Any],
    prediction: Dict[str, Any],
    maintenance_plan: Optional[Dict[str, Any]] = None,
    generation_method: str = "context_aware",
    battery_record_id: Optional[int] = None,
    report_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Execute the facts-first NLG pipeline.
    Returns a validated diagnostic report dictionary.
    """
    # 1. Input Validation and Normalization
    clean_telemetry, clean_prediction = validate_and_normalize_inputs(telemetry, prediction)

    # 2. Diagnostic Fact Extraction
    facts = extract_diagnostic_facts(clean_telemetry, clean_prediction, maintenance_plan)

    # 3. Diagnostic Rule Evaluation
    findings = evaluate_diagnostic_rules(facts)

    # 4. Content Planning
    raw_actions = []
    if maintenance_plan and "recommended_actions" in maintenance_plan:
        raw_actions = maintenance_plan["recommended_actions"]
    planned_content = plan_report_content(facts, findings, raw_actions=raw_actions)

    # 5. Text Realization
    method = generation_method if generation_method in ("baseline", "context_aware") else "context_aware"
    realized = realize_sentences(planned_content, method=method)

    # 6. Build Candidate Report Object
    now_iso = datetime.now(timezone.utc).isoformat()
    report_dict: Dict[str, Any] = {
        "report_id": report_id,
        "battery_record_id": battery_record_id,
        "generation_method": method,
        "condition_label": planned_content.condition_label,
        "health_score": planned_content.health_score,
        "summary": realized["summary"],
        "rendered_text": realized["rendered_text"],
        "measurements": planned_content.measurements,
        "findings": [f.to_dict() for f in planned_content.prioritized_findings],
        "recommended_actions": planned_content.prioritized_actions,
        "limitations": list(SYSTEM_LIMITATIONS),
        "provenance": {
            "model_active": planned_content.model_active,
            "prediction_source": planned_content.prediction_source,
            "evaluated_rules_count": len(findings)
        },
        "created_at": now_iso
    }

    # 7. Semantic & Schema Validation
    is_valid, validation_errors = validate_complete_report(
        report_dict, clean_telemetry, clean_prediction
    )

    if not is_valid:
        # Controlled handling of validation failure as per Section 4.2
        report_dict["validation_warning"] = "Report completed with validation notes."
        report_dict["validation_errors"] = validation_errors

    return report_dict
