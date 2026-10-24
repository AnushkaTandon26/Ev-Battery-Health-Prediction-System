"""
Report Content Planner.
Selects, prioritizes, aggregates findings, and structures the diagnostic report.
"""
from typing import List, Dict, Any
try:
    from backend.nlg.diagnostic_rules import DiagnosticFinding
    from backend.nlg.fact_extractor import DiagnosticFact
except ImportError:
    from nlg.diagnostic_rules import DiagnosticFinding
    from nlg.fact_extractor import DiagnosticFact

SEVERITY_ORDER = {
    "Critical": 0,
    "High": 1,
    "Medium": 2,
    "Low": 3,
    "Info": 4
}

ACTION_PRIORITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3
}


class PlannedReportContent:
    def __init__(
        self,
        condition_label: str,
        health_score: float,
        measurements: List[Dict[str, Any]],
        prioritized_findings: List[DiagnosticFinding],
        prioritized_actions: List[Dict[str, str]],
        model_active: bool,
        prediction_source: str
    ):
        self.condition_label = condition_label
        self.health_score = health_score
        self.measurements = measurements
        self.prioritized_findings = prioritized_findings
        self.prioritized_actions = prioritized_actions
        self.model_active = model_active
        self.prediction_source = prediction_source


def plan_report_content(
    facts: List[DiagnosticFact],
    findings: List[DiagnosticFinding],
    raw_actions: List[Dict[str, Any]] = None
) -> PlannedReportContent:
    """
    Plan and structure content:
    - Sort findings by severity (Critical -> High -> Medium -> Low -> Info)
    - Deduplicate similar findings
    - Structure measurement items
    - Prioritize and deduplicate recommended actions
    """
    # 1. Sort findings by severity
    sorted_findings = sorted(
        findings,
        key=lambda f: SEVERITY_ORDER.get(f.severity, 99)
    )

    # Deduplicate findings with identical rule_id
    seen_rules = set()
    deduped_findings: List[DiagnosticFinding] = []
    for f in sorted_findings:
        if f.rule_id not in seen_rules:
            seen_rules.add(f.rule_id)
            deduped_findings.append(f)

    # 2. Extract measurements
    measurements = []
    condition_label = "Safe"
    health_score = 85.0
    model_active = False
    prediction_source = "fallback_heuristic"

    for fact in facts:
        if fact.category in ("measurement", "derived"):
            measurements.append({
                "parameter": fact.parameter,
                "value": fact.value,
                "unit": fact.unit,
                "display_name": fact.display_name
            })
        elif fact.parameter == "status":
            condition_label = str(fact.value)
        elif fact.parameter == "health_score":
            health_score = float(fact.value)
            prediction_source = fact.source
            model_active = (fact.source == "keras_model")

    # If any finding is Critical or High, make sure condition label aligns
    if any(f.severity == "Critical" for f in deduped_findings):
        condition_label = "Critical"
    elif any(f.severity == "High" for f in deduped_findings) and condition_label == "Safe":
        condition_label = "Warning"

    # 3. Actions planning
    action_items: List[Dict[str, str]] = []
    seen_actions = set()

    # Default action if critical
    if condition_label == "Critical":
        action_items.append({
            "action": "Perform immediate pack safety isolation and schedule a certified technician inspection.",
            "priority": "critical"
        })
        seen_actions.add(action_items[-1]["action"])

    # From explicit recommendation facts
    for fact in facts:
        if fact.category == "recommendation" and fact.value:
            text = str(fact.value).strip()
            if text and text not in seen_actions:
                prio = "medium"
                if "technician" in text.lower() or "replace" in text.lower() or "immediate" in text.lower():
                    prio = "high"
                elif "track" in text.lower() or "log" in text.lower():
                    prio = "low"
                action_items.append({"action": text, "priority": prio})
                seen_actions.add(text)

    # If actions list is empty or raw_actions provided
    if raw_actions:
        for act in raw_actions:
            if isinstance(act, dict) and "action" in act:
                a_text = act["action"].strip()
                if a_text and a_text not in seen_actions:
                    action_items.append({
                        "action": a_text,
                        "priority": act.get("priority", "medium")
                    })
                    seen_actions.add(a_text)
            elif isinstance(act, str) and act.strip() and act.strip() not in seen_actions:
                action_items.append({"action": act.strip(), "priority": "medium"})
                seen_actions.add(act.strip())

    # Sort actions by priority
    action_items.sort(key=lambda a: ACTION_PRIORITY_ORDER.get(a.get("priority", "medium").lower(), 99))

    return PlannedReportContent(
        condition_label=condition_label,
        health_score=health_score,
        measurements=measurements,
        prioritized_findings=deduped_findings,
        prioritized_actions=action_items,
        model_active=model_active,
        prediction_source=prediction_source
    )
