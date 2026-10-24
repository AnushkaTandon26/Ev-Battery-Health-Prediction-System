"""
Diagnostic Rule Engine.
Evaluates configured criteria against extracted facts to produce traceable findings.
"""
from typing import List, Dict, Any
try:
    from backend.nlg.config import DIAGNOSTIC_THRESHOLDS
    from backend.nlg.fact_extractor import DiagnosticFact
except ImportError:
    from nlg.config import DIAGNOSTIC_THRESHOLDS
    from nlg.fact_extractor import DiagnosticFact

class DiagnosticFinding:
    def __init__(
        self,
        rule_id: str,
        severity: str,
        title: str,
        description: str,
        evidence_parameter: str,
        evidence_value: Any,
        qualification: str = ""
    ):
        self.rule_id = rule_id
        self.severity = severity  # "Info", "Low", "Medium", "High", "Critical"
        self.title = title
        self.description = description
        self.evidence_parameter = evidence_parameter
        self.evidence_value = evidence_value
        self.qualification = qualification

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "evidence_parameter": self.evidence_parameter,
            "evidence_value": self.evidence_value,
            "qualification": self.qualification
        }


def evaluate_diagnostic_rules(facts: List[DiagnosticFact]) -> List[DiagnosticFinding]:
    """
    Apply centralized diagnostic rules against facts to produce structured findings.
    """
    facts_by_param = {f.parameter: f for f in facts}
    findings: List[DiagnosticFinding] = []
    t = DIAGNOSTIC_THRESHOLDS

    # 1. Temperature evaluation
    if "temp" in facts_by_param:
        temp_val = facts_by_param["temp"].value
        if temp_val >= t["temp_critical"]:
            findings.append(
                DiagnosticFinding(
                    rule_id="RULE_TEMP_CRITICAL",
                    severity="Critical",
                    title="Critical temperature alert",
                    description=(
                        f"The recorded temperature of {temp_val} °C exceeds the critical threshold "
                        f"({t['temp_critical']} °C). Immediate cooling and thermal inspection are indicated."
                    ),
                    evidence_parameter="temp",
                    evidence_value=temp_val,
                    qualification="Observed reading crosses prototype safety margin; requires thermal check."
                )
            )
        elif temp_val >= t["temp_warning"]:
            findings.append(
                DiagnosticFinding(
                    rule_id="RULE_TEMP_HIGH",
                    severity="High",
                    title="Elevated pack temperature",
                    description=(
                        f"The measured temperature of {temp_val} °C crosses the prototype rule used by "
                        f"this project for a high-temperature concern ({t['temp_warning']} °C)."
                    ),
                    evidence_parameter="temp",
                    evidence_value=temp_val,
                    qualification="The report flags this measurement for review; it does not confirm an internal cell fault."
                )
            )

    # 2. State of Charge (SOC) evaluation
    if "soc" in facts_by_param:
        soc_val = facts_by_param["soc"].value
        if soc_val <= t["soc_critical_low"]:
            findings.append(
                DiagnosticFinding(
                    rule_id="RULE_SOC_CRITICAL_LOW",
                    severity="High",
                    title="Critically low charge level",
                    description=(
                        f"The State of Charge is critically low at {soc_val}%, falling below the reserve threshold "
                        f"({t['soc_critical_low']}%). Recharge recommended to avoid deep cell discharge."
                    ),
                    evidence_parameter="soc",
                    evidence_value=soc_val,
                    qualification="Deep discharge can accelerate electrode degradation."
                )
            )
        elif soc_val <= t["soc_warning_low"]:
            findings.append(
                DiagnosticFinding(
                    rule_id="RULE_SOC_LOW",
                    severity="Medium",
                    title="Low state of charge",
                    description=(
                        f"The State of Charge is low at {soc_val}%, which is within the advisory low-charge range."
                    ),
                    evidence_parameter="soc",
                    evidence_value=soc_val,
                    qualification="Standard operating range advisory."
                )
            )

    # 3. Voltage evaluation
    if "voltage" in facts_by_param:
        volt_val = facts_by_param["voltage"].value
        if volt_val < t["voltage_under"]:
            findings.append(
                DiagnosticFinding(
                    rule_id="RULE_VOLTAGE_UNDER",
                    severity="High",
                    title="Pack undervoltage detected",
                    description=(
                        f"Pack terminal voltage is {volt_val} V, below the minimum expected operational bound "
                        f"({t['voltage_under']} V)."
                    ),
                    evidence_parameter="voltage",
                    evidence_value=volt_val,
                    qualification="Indicates possible high pack sag or low cell balance."
                )
            )
        elif volt_val > t["voltage_over"]:
            findings.append(
                DiagnosticFinding(
                    rule_id="RULE_VOLTAGE_OVER",
                    severity="High",
                    title="Pack overvoltage detected",
                    description=(
                        f"Pack terminal voltage is {volt_val} V, exceeding the nominal upper bound ({t['voltage_over']} V)."
                    ),
                    evidence_parameter="voltage",
                    evidence_value=volt_val,
                    qualification="High voltage during fast charging or regenerative braking."
                )
            )

    # 4. Current evaluation
    if "current" in facts_by_param:
        curr_val = facts_by_param["current"].value
        if curr_val <= t["current_high_discharge"]:
            findings.append(
                DiagnosticFinding(
                    rule_id="RULE_CURRENT_HIGH_DISCHARGE",
                    severity="Medium",
                    title="High continuous discharge current",
                    description=(
                        f"Recorded current of {curr_val} A represents high discharge draw, exceeding normal cruising levels."
                    ),
                    evidence_parameter="current",
                    evidence_value=curr_val,
                    qualification="High load increases thermal accumulation and transient voltage sag."
                )
            )
        elif curr_val >= t["current_high_charge"]:
            findings.append(
                DiagnosticFinding(
                    rule_id="RULE_CURRENT_HIGH_CHARGE",
                    severity="Medium",
                    title="High charge/regenerative current",
                    description=(
                        f"Recorded charge current of {curr_val} A exceeds regular steady-state charging baseline."
                    ),
                    evidence_parameter="current",
                    evidence_value=curr_val,
                    qualification="Verify thermal stability during sustained high-rate energy input."
                )
            )

    # 5. Degradation level evaluation
    if "degradation_level" in facts_by_param:
        deg_val = facts_by_param["degradation_level"].value
        if deg_val >= t["degradation_high_level"]:
            findings.append(
                DiagnosticFinding(
                    rule_id="RULE_DEGRADATION_HIGH",
                    severity="High",
                    title="Substantial degradation index",
                    description=(
                        f"The provided degradation index is {deg_val}, indicating notable historical ageing or capacity offset."
                    ),
                    evidence_parameter="degradation_level",
                    evidence_value=deg_val,
                    qualification="Degradation semantics are qualified by the current system; wording is intentionally equivocal."
                )
            )
        elif deg_val >= t["degradation_review_level"]:
            findings.append(
                DiagnosticFinding(
                    rule_id="RULE_DEGRADATION_ELEVATED",
                    severity="Low",
                    title="Elevated degradation index",
                    description=(
                        f"The provided degradation index is {deg_val}, which is at or above the configured review level "
                        f"({t['degradation_review_level']}). This is a supplied index value and is not interpreted here as "
                        f"a specific percentage of capacity loss."
                    ),
                    evidence_parameter="degradation_level",
                    evidence_value=deg_val,
                    qualification="Degradation semantics are qualified by the current system; wording is intentionally equivocal."
                )
            )

    # 6. Overall Health Score / Status
    if "health_score" in facts_by_param:
        hs_val = facts_by_param["health_score"].value
        if hs_val < t["health_critical"]:
            findings.append(
                DiagnosticFinding(
                    rule_id="RULE_HEALTH_CRITICAL",
                    severity="Critical",
                    title="Critical battery health status",
                    description=(
                        f"The predicted health score is {hs_val}%, placing the battery pack in the Critical maintenance band."
                    ),
                    evidence_parameter="health_score",
                    evidence_value=hs_val,
                    qualification="Requires comprehensive pack diagnostic and maintenance evaluation."
                )
            )
        elif hs_val < t["health_warning"]:
            findings.append(
                DiagnosticFinding(
                    rule_id="RULE_HEALTH_WARNING",
                    severity="Medium",
                    title="Degraded health score warning",
                    description=(
                        f"The predicted health score is {hs_val}%, reflecting moderate health degradation."
                    ),
                    evidence_parameter="health_score",
                    evidence_value=hs_val,
                    qualification="Advisory condition for scheduled monitoring."
                )
            )

    return findings
