"""Centralized, versioned configuration for the NLG diagnostic layer.

This module is the single source of truth for the thresholds, severity
labels, units and wording used by the diagnostic report generator. It exists
because the existing code base embedded overlapping thresholds in
``backend/utils.py`` (prediction recommendations) and
``backend/agentic_ai.py`` (maintenance planner). Those modules keep their own
behaviour; this configuration *documents and reconciles* the values the report
layer uses so the generated text never silently contradicts them.

IMPORTANT (academic / safety note):
    None of the thresholds below are universal manufacturer limits. They are
    project-level review thresholds chosen for a demonstration pack and MUST be
    reconfigured for a specific battery chemistry and pack specification before
    any real-world interpretation. The report wording reflects this.
"""

from __future__ import annotations

# Version identifiers are persisted with every report for traceability /
# reproducibility (TRD NFR-04). Bump these when thresholds or wording change.
GENERATOR_VERSION = "nlg-1.0"
RULES_VERSION = "thresholds-1.0"
SCHEMA_VERSION = "1.0"

# Units are fixed and attached to every numeric fact so the realizer never
# has to guess them.
UNITS = {
    "voltage": "V",
    "current": "A",
    "soc": "%",
    "temperature": "°C",   # degree Celsius
    "degradation_level": "%",
    "health_score": "%",
    "power": "W",
}

# Human-facing labels for each parameter.
LABELS = {
    "voltage": "Voltage",
    "current": "Current",
    "soc": "State of Charge",
    "temperature": "Temperature",
    "degradation_level": "Degradation level",
    "health_score": "Predicted health score",
    "power": "Pack power (derived)",
}

# ---------------------------------------------------------------------------
# Validation ranges.
#
# These are *plausibility* ranges used to reject physically impossible or
# clearly mistyped input, NOT safe-operating limits. SOC and degradation are
# genuine 0-100 percentages. Voltage/current/temperature bounds are generous
# and configurable; they only guard against nonsense such as a 5000 V reading.
# ---------------------------------------------------------------------------
VALIDATION_RANGES = {
    "voltage": {"min": 0.0, "max": 1000.0, "required": True},
    "current": {"min": -1000.0, "max": 1000.0, "required": True},
    "soc": {"min": 0.0, "max": 100.0, "required": True},
    "temp": {"min": -40.0, "max": 120.0, "required": True},
    # degradation is optional by the legacy /api/predict contract (defaults 0)
    "degradation_level": {"min": 0.0, "max": 100.0, "required": False},
}

# ---------------------------------------------------------------------------
# Diagnostic rule thresholds.
#
# Each entry documents the value, where the equivalent value came from in the
# existing code, and the comparison semantics. The report layer uses THESE for
# its observations. They are intentionally aligned with the existing predictor
# and planner so the narrative agrees with the numbers the rest of the app
# already produces.
# ---------------------------------------------------------------------------
THRESHOLDS = {
    # Temperature review bands (°C). utils.py uses >40 for a cool-down
    # recommendation; agentic_ai uses 35/40/45 for planner tiers.
    "temperature": {
        "review_c": 35.0,     # elevated — worth watching (planner "medium")
        "high_c": 40.0,       # high — matches utils cool-down recommendation
        "critical_c": 45.0,   # critical — matches planner emergency trigger
    },
    # State of charge (%). utils.py and planner both act at <=20%.
    "soc": {
        "low_pct": 20.0,
        "very_low_pct": 10.0,
    },
    # Absolute current (A). utils uses abs>50; planner uses abs>=45 for a
    # separate moderate-stress trigger. We keep both, by purpose.
    "current": {
        "elevated_abs_a": 45.0,   # moderate stress (planner)
        "high_abs_a": 50.0,       # high rate (utils recommendation)
    },
    # Degradation (%). utils uses 20/35; planner uses 15/30/45.
    "degradation": {
        "review_pct": 15.0,
        "inspect_pct": 20.0,
        "high_pct": 30.0,
        "service_pct": 35.0,
    },
    # Health score (%). Status bands come straight from utils.predict:
    # <40 Critical, <70 Warning, else Safe. Extra "low" band for wording.
    "health": {
        "critical_pct": 40.0,
        "warning_pct": 70.0,
        "low_pct": 80.0,          # below this the planner flags condition review
    },
    # Minimum drop in health score across recent records to call it a trend.
    "trend": {
        "significant_drop_pct": 10.0,
        "min_records": 2,
    },
}

# Mapping from internal rule severity to the JSON-schema severity enum.
SEVERITY_ENUM = ["info", "low", "medium", "high", "critical", "unknown"]

# Recommendation priority enum from the schema.
PRIORITY_ENUM = ["low", "medium", "high", "critical"]

# Report length guardrail (NFR-05: 120-250 words target).
REPORT = {
    "max_summary_sentences": 4,
    "target_word_min": 120,
    "target_word_max": 250,
}

# Mandatory limitation / disclaimer sentences added to every report.
STANDARD_LIMITATIONS = [
    "This report is a decision-support summary and does not replace battery "
    "manufacturer guidance or a qualified technician's inspection.",
    "The review thresholds used here are project defaults, not certified "
    "manufacturer limits; compare each reading against the operating range "
    "specified for this battery pack.",
]

# Degradation semantics note. The project has not formally defined whether
# degradation_level means capacity loss, a normalized index or something else,
# so the report must use neutral wording and never assert "capacity loss".
DEGRADATION_SEMANTICS_NOTE = (
    "The degradation level is treated as a provided degradation index (0-100); "
    "its precise physical meaning is not defined by the current system, so it "
    "is not interpreted as a specific percentage of capacity loss."
)


def health_status(health_score):
    """Return Safe/Warning/Critical using the SAME bands as backend.utils.

    Kept here so tests and the report layer can derive a status consistently,
    but the predictor's returned status remains the source of truth at runtime.
    """
    if health_score is None:
        return "Unknown"
    if health_score < THRESHOLDS["health"]["critical_pct"]:
        return "Critical"
    if health_score < THRESHOLDS["health"]["warning_pct"]:
        return "Warning"
    return "Safe"
