"""
Report Service.
Bridges report generation, database persistence, and API formatting.
"""
import json
from typing import Dict, Any, Optional, List
try:
    from backend.database import db, DiagnosticReport, BatteryData
    from backend.nlg.report_generator import generate_diagnostic_report
except ImportError:
    from database import db, DiagnosticReport, BatteryData
    from nlg.report_generator import generate_diagnostic_report


def create_and_persist_report(
    telemetry: Dict[str, Any],
    prediction: Dict[str, Any],
    maintenance_plan: Optional[Dict[str, Any]] = None,
    battery_record_id: Optional[int] = None,
    generation_method: str = "context_aware"
) -> Dict[str, Any]:
    """
    Generate an NLG report and persist it to the SQLite database.
    """
    # 1. Generate the structured report
    report_dict = generate_diagnostic_report(
        telemetry=telemetry,
        prediction=prediction,
        maintenance_plan=maintenance_plan,
        generation_method=generation_method,
        battery_record_id=battery_record_id
    )

    # 2. Extract structured fields for persistence
    payload_data = {
        "measurements": report_dict.get("measurements", []),
        "findings": report_dict.get("findings", []),
        "recommended_actions": report_dict.get("recommended_actions", []),
        "limitations": report_dict.get("limitations", []),
        "provenance": report_dict.get("provenance", {})
    }

    report_record = DiagnosticReport(
        battery_record_id=battery_record_id,
        generation_method=report_dict.get("generation_method", "context_aware"),
        condition_label=report_dict.get("condition_label", "Safe"),
        health_score=report_dict.get("health_score"),
        summary=report_dict.get("summary", ""),
        rendered_text=report_dict.get("rendered_text", ""),
        report_data=json.dumps(payload_data)
    )

    db.session.add(report_record)
    db.session.commit()

    report_dict["report_id"] = report_record.id
    report_dict["id"] = report_record.id
    return report_dict


def get_recent_reports(limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve recent diagnostic reports."""
    reports = DiagnosticReport.query.order_by(DiagnosticReport.created_at.desc()).limit(limit).all()
    return [r.to_dict() for r in reports]


def get_report_by_id(report_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a single diagnostic report by its primary key ID."""
    report = DiagnosticReport.query.get(report_id)
    return report.to_dict() if report else None


def get_report_by_record_id(record_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve the report associated with a specific battery data record."""
    report = DiagnosticReport.query.filter_by(battery_record_id=record_id).order_by(DiagnosticReport.created_at.desc()).first()
    return report.to_dict() if report else None
