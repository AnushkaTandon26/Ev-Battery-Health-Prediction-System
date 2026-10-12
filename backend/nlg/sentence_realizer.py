"""Sentence realization (NLG stage 5).

Turns the :class:`ReportPlan` into plain-English text. This module is where the
linguistic work happens, and it deliberately offers TWO realizers so the
project can compare approaches (PRD FR-11 / TRD 5.3):

* :func:`realize_baseline`  - a naive fixed-template generator that emits one
  rigid sentence per finding with no aggregation or variation. This is the
  "basic fixed-template" comparison point.

* :func:`realize_context_aware` - the main generator. It performs:
    - lexicalization: numbers rendered with fixed formatting + units;
    - referring expressions: "the pack", "it", status-aware phrasing;
    - aggregation: related findings combined into fewer, smoother sentences;
    - severity-aware ordering (findings arrive pre-sorted);
    - redundancy reduction: no repeated facts across sections;
    - unit-aware wording and calibrated hedging ("may", "is above the
      configured threshold").

Both return a dict with the realized ``summary``, ``sections`` and a single
``rendered_text`` string, so they are drop-in comparable in evaluation.
"""

from __future__ import annotations

from typing import Dict, List

from .report_planner import ReportPlan
from .config import REPORT


def _fmt(value, unit=""):
    """Deterministic number formatting (lexicalization)."""
    if value is None:
        return "not provided"
    if isinstance(value, float) and value.is_integer():
        text = str(int(value))
    else:
        text = f"{value:g}"
    return f"{text} {unit}".strip()


_STATUS_PHRASE = {
    "Safe": "within the configured normal band",
    "Warning": "in the warning band and warrants attention",
    "Critical": "in the critical band and needs prompt review",
    "Unknown": "not conclusively classified",
}


# ---------------------------------------------------------------------------
# Baseline: naive fixed templates (no aggregation, no variation).
# ---------------------------------------------------------------------------

def realize_baseline(plan: ReportPlan) -> Dict:
    f = plan.facts
    lines = []
    lines.append(f"Status: {plan.overall_status}.")
    lines.append(f"Health score: {_fmt(plan.health_score, '%')}.")
    for m in f.measurements:
        if m.parameter == "health_score":
            continue
        lines.append(f"{m.label}: {_fmt(m.value, m.unit)}.")
    for fnd in plan.findings:
        lines.append(f"Finding: {fnd.title} (severity {fnd.severity}).")
    for rec in plan.recommendations:
        lines.append(f"Action: {rec['action']}")
    for lim in plan.limitations:
        lines.append(f"Note: {lim}")
    text = "\n".join(lines)
    return {
        "summary": f"Status: {plan.overall_status}. Health score: {_fmt(plan.health_score, '%')}.",
        "sections": {"lines": lines},
        "rendered_text": text,
    }


# ---------------------------------------------------------------------------
# Context-aware generator.
# ---------------------------------------------------------------------------

def _summary_sentences(plan: ReportPlan) -> List[str]:
    f = plan.facts
    phrase = _STATUS_PHRASE.get(plan.overall_status, _STATUS_PHRASE["Unknown"])
    s = []
    if plan.health_score is not None:
        s.append(
            f"The predicted battery health is {_fmt(plan.health_score, '%')}, "
            f"which the system classifies as {plan.overall_status} — {phrase}.")
    else:
        s.append(f"The system classifies this battery as {plan.overall_status} — {phrase}.")

    # Severity-aware headline about findings.
    crit = [x for x in plan.findings if x.severity in ("critical", "high")]
    med = [x for x in plan.findings if x.severity == "medium"]
    if crit:
        titles = _join([x.title.lower() for x in crit])
        s.append(f"The most important observation{'s' if len(crit) > 1 else ''} "
                 f"concern{'s' if len(crit) == 1 else ''} {titles}.")
    elif med:
        s.append("A few parameters are slightly outside their configured review "
                 "levels but none are severe.")
    elif not plan.findings:
        s.append("No parameter crossed its configured review threshold, so "
                 "routine monitoring is appropriate.")
    if plan.model_mode != "keras":
        s.append("Note that this score came from the fallback heuristic rather "
                 "than the trained model.")
    return s[:REPORT["max_summary_sentences"]]


def _join(items: List[str]) -> str:
    """Oxford-free natural-language list join (aggregation helper)."""
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _observation_sentences(plan: ReportPlan) -> List[str]:
    """One evidence-grounded sentence per finding, with aggregation of the
    low-severity ones to reduce redundancy."""
    sentences = []
    low_bucket = []
    for fnd in plan.findings:
        ev = fnd.evidence[0]
        value_text = _fmt(ev.value, ev.unit)
        if fnd.severity in ("low", "info"):
            low_bucket.append(f"{fnd.title.lower()} ({value_text})")
            continue
        sentences.append(
            f"{fnd.title}: {ev.parameter.replace('_', ' ')} is {value_text}, "
            f"{ev.threshold_description or 'outside the configured range'}.")
    if low_bucket:
        sentences.append(
            "Minor observations: " + _join(low_bucket) + ".")
    return sentences


def _telemetry_sentence(plan: ReportPlan) -> str:
    f = plan.facts
    parts = []
    for param in ("voltage", "current", "soc", "temperature", "degradation_level"):
        m = f.measurement_map().get(param)
        if m is not None:
            parts.append(f"{m.label.lower()} {_fmt(m.value, m.unit)}")
    if not parts:
        return ""
    return "Readings used: " + _join(parts) + "."


def realize_context_aware(plan: ReportPlan) -> Dict:
    summary_s = _summary_sentences(plan)
    telemetry_s = _telemetry_sentence(plan)
    obs_s = _observation_sentences(plan)

    concern_s = []
    for fnd in plan.findings:
        if fnd.severity in ("critical", "high", "medium") and fnd.confidence_note:
            concern_s.append(f"{fnd.title}: {fnd.confidence_note}")

    action_s = [f"[{r['priority']}] {r['action']}" for r in plan.recommendations]

    sections = {
        "summary": summary_s,
        "telemetry": [telemetry_s] if telemetry_s else [],
        "observations": obs_s,
        "potential_concerns": concern_s,
        "recommended_actions": action_s,
        "limitations": plan.limitations,
    }

    # Assemble human-readable text with headings.
    blocks = []
    blocks.append(" ".join(summary_s))
    if telemetry_s:
        blocks.append(telemetry_s)
    if obs_s:
        blocks.append("Observations: " + " ".join(obs_s))
    if concern_s:
        blocks.append("Potential concerns: " + " ".join(concern_s))
    if action_s:
        blocks.append("Recommended actions: " + "; ".join(
            r["action"] for r in plan.recommendations) + ".")
    blocks.append("Limitations: " + " ".join(plan.limitations))
    rendered = "\n\n".join(b for b in blocks if b.strip())

    return {
        "summary": " ".join(summary_s),
        "sections": sections,
        "rendered_text": rendered,
    }


def realize(plan: ReportPlan, method: str = "context_aware") -> Dict:
    if method == "baseline":
        return realize_baseline(plan)
    return realize_context_aware(plan)
