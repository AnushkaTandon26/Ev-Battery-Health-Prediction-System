"""
Sentence Realizer for Diagnostic Reports.
Provides both:
1. Baseline Generator (fixed deterministic templates)
2. Context-Aware Generator (nuanced aggregation, conservative hedging, fallback disclosure)
"""
from typing import Dict, Any, List
try:
    from backend.nlg.report_planner import PlannedReportContent
    from backend.nlg.config import SYSTEM_LIMITATIONS
except ImportError:
    from nlg.report_planner import PlannedReportContent
    from nlg.config import SYSTEM_LIMITATIONS


def realize_baseline_text(plan: PlannedReportContent) -> Dict[str, str]:
    """
    Fixed template deterministic realization.
    """
    # 1. Summary
    summary = (
        f"Battery status is {plan.condition_label} with a predicted health score of {plan.health_score}%. "
        f"System evaluated {len(plan.measurements)} readings and generated {len(plan.prioritized_findings)} findings."
    )

    # 2. Key findings narrative
    if plan.prioritized_findings:
        findings_lines = [
            f"- [{f.severity}] {f.title}: {f.description}"
            for f in plan.prioritized_findings
        ]
        findings_text = "\n".join(findings_lines)
    else:
        findings_text = "All evaluated parameters are within nominal prototype thresholds."

    # 3. Actions
    if plan.prioritized_actions:
        actions_lines = [
            f"- [{a.get('priority', 'medium').upper()}] {a['action']}"
            for a in plan.prioritized_actions
        ]
        actions_text = "\n".join(actions_lines)
    else:
        actions_text = "Continue standard operational schedule and periodic review."

    rendered_text = (
        f"DIAGNOSTIC REPORT (BASELINE)\n\n"
        f"Status: {plan.condition_label} | Health Score: {plan.health_score}%\n\n"
        f"SUMMARY:\n{summary}\n\n"
        f"FINDINGS:\n{findings_text}\n\n"
        f"RECOMMENDED ACTIONS:\n{actions_text}\n"
    )

    return {
        "summary": summary,
        "rendered_text": rendered_text
    }


def realize_context_aware_text(plan: PlannedReportContent) -> Dict[str, str]:
    """
    Context-aware natural language realization.
    Follows conservative diagnostic style, qualified semantics, and explicit evidence links.
    """
    # Model provenance disclosure
    if plan.model_active:
        provenance_clause = "The score was computed by the active machine learning sequence model."
    else:
        provenance_clause = "Note that this score came from the fallback heuristic rather than the trained model."

    # Summary synthesis based on condition
    if plan.condition_label == "Safe":
        if not plan.prioritized_findings:
            summary = (
                f"The predicted battery health is {plan.health_score}%, which the system classifies as Safe "
                f"— within the configured normal band. {provenance_clause} All observed telemetry readings remain "
                f"within nominal prototype operating thresholds."
            )
        else:
            noteworthy_titles = ", ".join(f.title.lower() for f in plan.prioritized_findings[:2])
            summary = (
                f"The predicted battery health is {plan.health_score}%, which the system classifies as Safe "
                f"— within the configured normal band. {provenance_clause} However, advisory observations ({noteworthy_titles}) "
                f"were flagged for scheduled tracking."
            )
    elif plan.condition_label == "Warning":
        findings_context = []
        for f in plan.prioritized_findings:
            if f.evidence_parameter == "soc":
                findings_context.append(f"State of Charge is low at {f.evidence_value}%")
            elif f.evidence_parameter == "temp":
                findings_context.append(f"measured temperature of {f.evidence_value} °C crosses the high-temperature rule")
            elif f.evidence_parameter == "degradation_level":
                findings_context.append(f"degradation index is elevated at {f.evidence_value}")
            elif f.evidence_parameter == "voltage":
                findings_context.append(f"pack voltage is abnormal at {f.evidence_value} V")

        evidence_str = "; ".join(findings_context) if findings_context else "operational indicators warrant attention"
        summary = (
            f"The prediction indicates that the battery condition needs attention ({plan.condition_label}). "
            f"The health score is {plan.health_score}%. {provenance_clause} Key observations: {evidence_str}. "
            f"The report flags these measurements for review; it does not confirm an internal battery fault."
        )
    else:  # Critical
        summary = (
            f"The diagnostic evaluation marks the battery condition as Critical with a health score of {plan.health_score}%. "
            f"{provenance_clause} Severe conditions were detected that require immediate safety isolation and inspection."
        )

    # Narrative generation
    findings_blocks = []
    for f in plan.prioritized_findings:
        findings_blocks.append(
            f"• [{f.severity}] {f.title}: {f.description} ({f.qualification})"
        )
    findings_text = "\n".join(findings_blocks) if findings_blocks else "• No active anomalies detected."

    actions_blocks = []
    for a in plan.prioritized_actions:
        actions_blocks.append(f"• [{a.get('priority', 'medium')}] {a['action']}")
    actions_text = "\n".join(actions_blocks) if actions_blocks else "• Routine monitoring recommended."

    limitations_text = "\n".join(f"• {lim}" for lim in SYSTEM_LIMITATIONS)

    rendered_text = (
        f"NATURAL-LANGUAGE BATTERY DIAGNOSTIC REPORT\n"
        f"Condition: {plan.condition_label} | Health Score: {plan.health_score}%\n\n"
        f"SUMMARY:\n{summary}\n\n"
        f"KEY FINDINGS:\n{findings_text}\n\n"
        f"SUGGESTED NEXT CHECKS:\n{actions_text}\n\n"
        f"LIMITATIONS:\n{limitations_text}\n"
    )

    return {
        "summary": summary,
        "rendered_text": rendered_text
    }


def realize_sentences(plan: PlannedReportContent, method: str = "context_aware") -> Dict[str, str]:
    """
    Produce natural-language text using the requested realization method.
    """
    if method == "baseline":
        return realize_baseline_text(plan)
    return realize_context_aware_text(plan)
