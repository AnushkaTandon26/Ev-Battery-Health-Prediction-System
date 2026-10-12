"""Flask-facing service helpers for diagnostic report generation and storage.

Thin layer between the Flask routes in ``app.py`` and the pure NLG pipeline in
``backend/nlg``. Keeps the route handlers short and keeps DB/transaction logic
in one place. Importing this module does not import the NLG package until a
function is called, so the app still starts if an optional dependency is absent.
"""

from __future__ import annotations

import json
from typing import Dict, Any, Optional, Tuple


def generate_and_store(
    db, DiagnosticReport, battery_record_id: int,
    telemetry: Dict[str, Any], prediction: Dict[str, Any],
    *, recent_records=None, maintenance_plan=None,
    method: str = "context_aware", commit: bool = True,
) -> Tuple[Optional[object], Dict[str, Any]]:
    """Generate a report and persist it.

    Returns ``(report_row_or_None, envelope)`` where envelope is the dict from
    ``nlg.report_generator.generate_report``. Persistence only happens on a
    successful, validated report. A failure does NOT raise, so the caller's
    prediction/maintenance commit is unaffected.
    """
    from nlg.report_generator import generate_report  # local import

    envelope = generate_report(
        telemetry, prediction, record_id=battery_record_id,
        recent_records=recent_records, maintenance_plan=maintenance_plan,
        method=method)

    if envelope["report_status"] != "generated" or not envelope["report"]:
        return None, envelope

    report = envelope["report"]
    schema_payload = {k: v for k, v in report.items() if not k.startswith("_")}

    row = DiagnosticReport(
        battery_record_id=battery_record_id,
        report_json=json.dumps(schema_payload),
        rendered_text=report.get("_rendered_text", ""),
        generation_method=report.get("generation_method", "template_nlg"),
        model_status=report.get("model_status", "unknown"),
        source_snapshot=json.dumps(report.get("source_snapshot", {})),
        generator_version=report.get("_generator_version", "nlg-1.0"),
        rules_version=report.get("_rules_version", "thresholds-1.0"),
        schema_version=report.get("schema_version", "1.0"),
        generation_status="generated",
        error_code=None,
    )
    db.session.add(row)
    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return row, envelope
