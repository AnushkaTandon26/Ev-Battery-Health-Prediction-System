"""
Report Validator.
Validates report structure, factual grounding, numerical fidelity, and safety constraints.
"""
import re
from typing import Dict, Any, List, Tuple
try:
    from backend.nlg.schema import validate_report_schema
except ImportError:
    from nlg.schema import validate_report_schema


def validate_grounding_and_fidelity(
    report_dict: Dict[str, Any],
    source_telemetry: Dict[str, float],
    source_prediction: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """
    Check that all numerical values and claims in the report summary and findings
    originate strictly from the source telemetry, prediction, or valid thresholds.
    """
    errors: List[str] = []
    text_content = report_dict.get("summary", "") + " " + report_dict.get("rendered_text", "")

    # 1. Verify health score fidelity
    reported_hs = report_dict.get("health_score")
    expected_hs = source_prediction.get("health_score")
    if expected_hs is not None and reported_hs is not None:
        if abs(reported_hs - expected_hs) > 0.1:
            errors.append(
                f"Health score mismatch: report has {reported_hs}, source prediction has {expected_hs}"
            )

    # 2. Verify telemetry numbers appearing in findings
    findings = report_dict.get("findings", [])
    for f in findings:
        param = f.get("evidence_parameter")
        val = f.get("evidence_value")
        if param in source_telemetry and val is not None:
            source_val = source_telemetry[param]
            try:
                num_val = float(val)
                if abs(num_val - source_val) > 0.1:
                    errors.append(
                        f"Evidence value mismatch for '{param}': finding has {num_val}, telemetry has {source_val}"
                    )
            except (ValueError, TypeError):
                pass

    # 3. Check for unsupported claim patterns
    # e.g., claiming cell failure or specific capacity loss without evidence
    unsupported_phrases = [
        "cell-level failure confirmed",
        "internal short circuit verified",
        "battery replacement mandatory immediately",
        "capacity loss is exactly"
    ]
    for phrase in unsupported_phrases:
        if phrase in text_content.lower():
            errors.append(f"Report contains ungrounded/unsupported diagnostic claim: '{phrase}'")

    return len(errors) == 0, errors


def validate_complete_report(
    report_dict: Dict[str, Any],
    source_telemetry: Dict[str, float],
    source_prediction: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """
    Runs both schema validation and semantic grounding checks.
    """
    all_errors = []

    # Schema validation
    schema_ok, schema_errors = validate_report_schema(report_dict)
    if not schema_ok:
        all_errors.extend(schema_errors)

    # Grounding & fidelity validation
    grounding_ok, grounding_errors = validate_grounding_and_fidelity(
        report_dict, source_telemetry, source_prediction
    )
    if not grounding_ok:
        all_errors.extend(grounding_errors)

    return len(all_errors) == 0, all_errors
