"""Report content planning (NLG stage 4).

Decides WHAT goes into the report and in WHAT ORDER, separately from how the
sentences are phrased (that is the realizer's job). Keeping planning and
realization apart is what lets us evaluate the "context-aware" generator
against a naive fixed-template baseline (PRD FR-11, TRD 5.2).

The planner also maps findings and the existing maintenance plan to a
de-duplicated, prioritized recommendation list whose every item is traceable
to a finding code or the maintenance planner (schema: recommendation.source).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from .config import THRESHOLDS, STANDARD_LIMITATIONS, DEGRADATION_SEMANTICS_NOTE
from .fact_extractor import DiagnosticFacts
from .diagnostic_rules import Finding


# Severity -> recommendation priority mapping.
_SEV_TO_PRIORITY = {
    "critical": "critical", "high": "high", "medium": "medium",
    "low": "low", "info": "low", "unknown": "low",
}

# Canonical actions tied to finding codes. Each is grounded: it only appears
# when the matching finding fired. Wording is cautious/decision-support.
_FINDING_ACTIONS = {
    "TEMPERATURE_HIGH": (
        "Check the cooling path and compare the temperature with the pack's "
        "rated operating range before heavy use."),
    "SOC_LOW": (
        "Recharge the battery before the next trip if the remaining range is "
        "insufficient for the planned use."),
    "CURRENT_HIGH": (
        "Moderate the charge/discharge rate and review the load profile."),
    "DEGRADATION_ELEVATED": (
        "Schedule a technician inspection of cell balancing and pack condition."),
    "HEALTH_SCORE_LOW": (
        "Plan a battery condition review; monitor the health score on the next "
        "cycles."),
    "HEALTH_DECLINING": (
        "Monitor the health trend closely and escalate if the decline continues."),
}


@dataclass
class ReportPlan:
    overall_status: str
    health_score: Optional[float]
    model_mode: str
    findings: List[Finding]
    conflicts: List[str]
    recommendations: List[Dict[str, Any]]     # schema recommendation objects
    limitations: List[str]
    include_trend: bool
    facts: DiagnosticFacts


def _plan_recommendations(facts, findings):
    """Build de-duplicated, prioritized recommendations.

    Priority: finding-derived actions first (ordered by severity), then any
    additional actions from the existing maintenance plan that are not already
    covered. Existing predictor ``recommendations`` are reused as rule-sourced
    actions when they map to a finding, otherwise surfaced generically.
    """
    recs = []
    seen_actions = set()

    def push(priority, action, reason, source, codes):
        key = action.strip().lower()
        if key in seen_actions:
            return
        seen_actions.add(key)
        recs.append({
            "priority": priority, "action": action, "reason": reason,
            "source": source, "related_finding_codes": codes,
        })

    for fnd in findings:  # already severity-sorted
        action = _FINDING_ACTIONS.get(fnd.code)
        if action:
            push(_SEV_TO_PRIORITY.get(fnd.severity, "low"), action,
                 f"Linked to finding {fnd.code} ({fnd.title}).", "rule",
                 [fnd.code])

    # Fold in maintenance-planner actions (do not invent new ones).
    plan = facts.maintenance_plan or {}
    plan_priority = (plan.get("priority") or "").lower()
    mapped_priority = plan_priority if plan_priority in {
        "low", "medium", "high", "critical"} else "medium"
    for action in plan.get("recommended_actions", []) or []:
        push(mapped_priority, action,
             f"From the maintenance plan ({plan.get('title', 'planned action')}).",
             "maintenance_planner", [])

    # Order recommendations by priority.
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    recs.sort(key=lambda r: order.get(r["priority"], 9))
    return recs


def _plan_limitations(facts, conflicts):
    limitations = list(STANDARD_LIMITATIONS)
    if facts.degradation_level is not None:
        limitations.append(DEGRADATION_SEMANTICS_NOTE)
    if facts.model_mode != "keras":
        limitations.append(
            "The health score was produced by the fallback heuristic because "
            "the trained model was unavailable; it is indicative, not a "
            "validated model prediction.")
    if facts.missing_fields:
        limitations.append(
            "Missing inputs: " + ", ".join(facts.missing_fields) +
            ". Observations for those parameters could not be produced.")
    if facts.trend is None:
        limitations.append(
            "Not enough ordered history was available to assess a health trend.")
    # Conflicts are also surfaced as limitations so they are never hidden.
    limitations.extend(conflicts)
    return limitations


def plan_report(facts: DiagnosticFacts, findings: List[Finding],
                conflicts: List[str]) -> ReportPlan:
    recommendations = _plan_recommendations(facts, findings)
    limitations = _plan_limitations(facts, conflicts)
    return ReportPlan(
        overall_status=facts.status,
        health_score=facts.health_score,
        model_mode=facts.model_mode,
        findings=findings,
        conflicts=conflicts,
        recommendations=recommendations,
        limitations=limitations,
        include_trend=facts.trend is not None,
        facts=facts,
    )
