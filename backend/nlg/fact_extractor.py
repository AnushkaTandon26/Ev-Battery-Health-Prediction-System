"""
Diagnostic Fact Extractor.
Translates normalized telemetry and model prediction outputs into structured facts.
"""
from typing import Dict, Any, List

class DiagnosticFact:
    def __init__(
        self,
        fact_id: str,
        category: str,
        parameter: str,
        value: Any,
        unit: str = "",
        display_name: str = "",
        source: str = "telemetry"
    ):
        self.fact_id = fact_id
        self.category = category  # "measurement", "prediction", "derived", "recommendation"
        self.parameter = parameter
        self.value = value
        self.unit = unit
        self.display_name = display_name or parameter
        self.source = source

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fact_id": self.fact_id,
            "category": self.category,
            "parameter": self.parameter,
            "value": self.value,
            "unit": self.unit,
            "display_name": self.display_name,
            "source": self.source
        }


def extract_diagnostic_facts(
    telemetry: Dict[str, float],
    prediction: Dict[str, Any],
    maintenance_plan: Dict[str, Any] = None
) -> List[DiagnosticFact]:
    """
    Extract a list of distinguishable diagnostic facts from inputs.
    """
    facts: List[DiagnosticFact] = []

    # 1. Measurement facts
    param_meta = {
        "voltage": ("Voltage", "V"),
        "current": ("Current", "A"),
        "soc": ("State of Charge", "%"),
        "temp": ("Temperature", "°C"),
        "degradation_level": ("Degradation level", "%")
    }

    for param, (name, unit) in param_meta.items():
        if param in telemetry:
            facts.append(
                DiagnosticFact(
                    fact_id=f"fact_{param}",
                    category="measurement",
                    parameter=param,
                    value=telemetry[param],
                    unit=unit,
                    display_name=name,
                    source="telemetry"
                )
            )

    # 2. Derived facts (e.g. instantaneous pack power)
    if "voltage" in telemetry and "current" in telemetry:
        pack_power = round(telemetry["voltage"] * telemetry["current"], 2)
        facts.append(
            DiagnosticFact(
                fact_id="fact_pack_power",
                category="derived",
                parameter="pack_power",
                value=pack_power,
                unit="W",
                display_name="Pack power (derived)",
                source="computed"
            )
        )

    # 3. Prediction facts
    health_score = prediction.get("health_score", 85.0)
    status = prediction.get("status", "Safe")
    model_active = prediction.get("model_active", False)

    facts.append(
        DiagnosticFact(
            fact_id="fact_health_score",
            category="prediction",
            parameter="health_score",
            value=health_score,
            unit="%",
            display_name="Predicted health score",
            source="keras_model" if model_active else "fallback_heuristic"
        )
    )
    facts.append(
        DiagnosticFact(
            fact_id="fact_status",
            category="prediction",
            parameter="status",
            value=status,
            unit="",
            display_name="Condition Status",
            source="predictor"
        )
    )

    # 4. Recommendation facts
    # From maintenance plan or prediction recommendations
    recs = []
    if maintenance_plan and "recommended_actions" in maintenance_plan:
        recs.extend(maintenance_plan["recommended_actions"])
    elif "recommendations" in prediction:
        recs.extend(prediction["recommendations"])

    for idx, rec in enumerate(recs):
        if isinstance(rec, dict):
            action_text = rec.get("action", "")
            prio = rec.get("priority", "medium")
        else:
            action_text = str(rec)
            prio = "medium"

        facts.append(
            DiagnosticFact(
                fact_id=f"fact_rec_{idx}",
                category="recommendation",
                parameter="recommended_action",
                value=action_text,
                unit="",
                display_name=f"Action ({prio})",
                source="maintenance_planner"
            )
        )

    return facts
