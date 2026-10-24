"""
Synthetic Evaluation Corpus.
Contains 10 curated diagnostic scenarios for comparative evaluation of the NLG pipeline.
"""

SYNTHETIC_SCENARIOS = [
    {
        "id": "scenario_01_nominal_cruising",
        "name": "Nominal Highway Cruising",
        "telemetry": {"voltage": 398.0, "current": -22.0, "soc": 72.0, "temp": 28.0, "degradation_level": 4.0},
        "prediction": {"health_score": 93.0, "status": "Safe", "model_active": False},
        "expected_findings": [],
        "expected_actions": [],
        "reference_text": "Battery condition is safe with healthy operating voltage and thermal stability. Routine checks advised."
    },
    {
        "id": "scenario_02_low_soc_warning",
        "name": "Low State of Charge Advisory",
        "telemetry": {"voltage": 365.0, "current": -18.0, "soc": 20.0, "temp": 31.0, "degradation_level": 8.0},
        "prediction": {"health_score": 88.0, "status": "Safe", "model_active": False},
        "expected_findings": ["RULE_SOC_LOW"],
        "expected_actions": [],
        "reference_text": "State of charge is low at twenty percent. Recharge recommended before deep discharge occurs."
    },
    {
        "id": "scenario_03_critical_low_soc",
        "name": "Critically Depleted Charge",
        "telemetry": {"voltage": 345.0, "current": -12.0, "soc": 11.0, "temp": 30.0, "degradation_level": 12.0},
        "prediction": {"health_score": 82.0, "status": "Warning", "model_active": False},
        "expected_findings": ["RULE_SOC_CRITICAL_LOW"],
        "expected_actions": [],
        "reference_text": "Critical low state of charge observed at eleven percent. Immediate recharging is needed."
    },
    {
        "id": "scenario_04_elevated_temperature",
        "name": "High Operating Temperature",
        "telemetry": {"voltage": 388.0, "current": -45.0, "soc": 55.0, "temp": 44.0, "degradation_level": 10.0},
        "prediction": {"health_score": 79.0, "status": "Warning", "model_active": False},
        "expected_findings": ["RULE_TEMP_HIGH"],
        "expected_actions": [],
        "reference_text": "Elevated pack temperature of forty-four degrees Celsius detected under sustained load. Review thermal cooling."
    },
    {
        "id": "scenario_05_critical_thermal_runaway_risk",
        "name": "Critical Pack Thermal Alert",
        "telemetry": {"voltage": 380.0, "current": -55.0, "soc": 50.0, "temp": 51.0, "degradation_level": 14.0},
        "prediction": {"health_score": 45.0, "status": "Critical", "model_active": False},
        "expected_findings": ["RULE_TEMP_CRITICAL", "RULE_HEALTH_CRITICAL"],
        "expected_actions": ["Perform immediate pack safety isolation"],
        "reference_text": "Critical thermal threshold exceeded at fifty-one degrees Celsius with health score forty-five. Immediate pack inspection required."
    },
    {
        "id": "scenario_06_high_discharge_current",
        "name": "Aggressive Acceleration Discharge",
        "telemetry": {"voltage": 360.0, "current": -75.0, "soc": 60.0, "temp": 36.0, "degradation_level": 10.0},
        "prediction": {"health_score": 81.0, "status": "Warning", "model_active": False},
        "expected_findings": ["RULE_CURRENT_HIGH_DISCHARGE"],
        "expected_actions": [],
        "reference_text": "High discharge current recorded exceeding normal operating band. Monitor thermal buildup and cell balance."
    },
    {
        "id": "scenario_07_fast_charging_regen",
        "name": "High Regen / Fast Charge Inflow",
        "telemetry": {"voltage": 415.0, "current": 70.0, "soc": 85.0, "temp": 38.0, "degradation_level": 8.0},
        "prediction": {"health_score": 89.0, "status": "Safe", "model_active": False},
        "expected_findings": ["RULE_CURRENT_HIGH_CHARGE"],
        "expected_actions": [],
        "reference_text": "Elevated charge current recorded during fast energy intake. Validate pack stability and temperature rise."
    },
    {
        "id": "scenario_08_elevated_degradation_index",
        "name": "Elevated Degradation Advisory",
        "telemetry": {"voltage": 395.0, "current": -15.0, "soc": 80.0, "temp": 26.0, "degradation_level": 22.0},
        "prediction": {"health_score": 86.0, "status": "Safe", "model_active": False},
        "expected_findings": ["RULE_DEGRADATION_ELEVATED"],
        "expected_actions": [],
        "reference_text": "Supplied degradation index is elevated at twenty-two. Qualify reading as supplied index and schedule pack check."
    },
    {
        "id": "scenario_09_severe_pack_sag_undervoltage",
        "name": "Severe Voltage Sag Under Load",
        "telemetry": {"voltage": 332.0, "current": -65.0, "soc": 25.0, "temp": 33.0, "degradation_level": 18.0},
        "prediction": {"health_score": 68.0, "status": "Warning", "model_active": False},
        "expected_findings": ["RULE_VOLTAGE_UNDER", "RULE_CURRENT_HIGH_DISCHARGE"],
        "expected_actions": [],
        "reference_text": "Pack undervoltage sag detected at 332 V under heavy current draw. Check cell impedance and balancing."
    },
    {
        "id": "scenario_10_composite_stress_example",
        "name": "Composite High-Stress Example (Report Section 5.6)",
        "telemetry": {"voltage": 360.0, "current": -55.0, "soc": 12.0, "temp": 47.0, "degradation_level": 40.0},
        "prediction": {"health_score": 48.1, "status": "Warning", "model_active": False},
        "expected_findings": ["RULE_TEMP_HIGH", "RULE_SOC_CRITICAL_LOW", "RULE_DEGRADATION_HIGH", "RULE_HEALTH_CRITICAL"],
        "expected_actions": [],
        "reference_text": "Diagnostic summary indicates battery needs attention. State of charge is low at twelve percent, temperature is forty-seven degrees."
    }
]
