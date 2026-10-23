"""
Schema validation module for diagnostic reports.
Validates report dictionaries against the JSON Schema Draft 2020-12 specification.
"""
import json
from pathlib import Path
from typing import Dict, Any, Tuple, List

SCHEMA_PATH = Path(__file__).resolve().parent / "diagnostic_report.schema.json"


def load_report_schema() -> Dict[str, Any]:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_report_schema(report_dict: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a report dictionary against the schema definition.
    Returns (is_valid, error_messages).
    """
    errors = []
    
    # Try importing jsonschema if present
    try:
        import jsonschema
        schema = load_report_schema()
        validator = jsonschema.Draft202012Validator(schema)
        schema_errors = list(validator.iter_errors(report_dict))
        if schema_errors:
            return False, [f"{e.json_path}: {e.message}" for e in schema_errors]
        return True, []
    except ImportError:
        pass

    # Fallback built-in validator ensuring structural conformance
    required_top = [
        "generation_method",
        "condition_label",
        "summary",
        "measurements",
        "findings",
        "recommended_actions",
        "limitations",
        "created_at"
    ]
    for field in required_top:
        if field not in report_dict:
            errors.append(f"Missing required field: '{field}'")
            
    if "generation_method" in report_dict and report_dict["generation_method"] not in ("baseline", "context_aware"):
        errors.append(f"Invalid generation_method: {report_dict['generation_method']}")
        
    if "condition_label" in report_dict and report_dict["condition_label"] not in ("Safe", "Warning", "Critical"):
        errors.append(f"Invalid condition_label: {report_dict['condition_label']}")
        
    if "summary" in report_dict and (not isinstance(report_dict["summary"], str) or len(report_dict["summary"]) < 10):
        errors.append("Field 'summary' must be a non-empty string of at least 10 characters.")
        
    if not isinstance(report_dict.get("measurements"), list):
        errors.append("Field 'measurements' must be a list.")
    else:
        for idx, m in enumerate(report_dict["measurements"]):
            for mf in ["parameter", "value", "unit"]:
                if mf not in m:
                    errors.append(f"measurements[{idx}] missing '{mf}'")

    if not isinstance(report_dict.get("findings"), list):
        errors.append("Field 'findings' must be a list.")
    else:
        for idx, f in enumerate(report_dict["findings"]):
            for ff in ["rule_id", "severity", "title", "description", "evidence_parameter", "evidence_value"]:
                if ff not in f:
                    errors.append(f"findings[{idx}] missing '{ff}'")

    if not isinstance(report_dict.get("recommended_actions"), list):
        errors.append("Field 'recommended_actions' must be a list.")
    else:
        for idx, a in enumerate(report_dict["recommended_actions"]):
            for af in ["action", "priority"]:
                if af not in a:
                    errors.append(f"recommended_actions[{idx}] missing '{af}'")

    if not isinstance(report_dict.get("limitations"), list):
        errors.append("Field 'limitations' must be a list.")

    return len(errors) == 0, errors
