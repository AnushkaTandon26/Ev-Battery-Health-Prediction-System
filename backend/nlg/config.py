"""
Central configuration for diagnostic thresholds and reporting rules.
These thresholds serve as prototype rules for the NLG demonstration.
"""

DIAGNOSTIC_THRESHOLDS = {
    # Temperature thresholds in Celsius
    "temp_normal_max": 35.0,
    "temp_warning": 42.0,
    "temp_critical": 48.0,
    
    # State of Charge thresholds in percentage (0 - 100)
    "soc_critical_low": 15.0,
    "soc_warning_low": 25.0,
    "soc_normal_high": 90.0,
    
    # Pack Voltage thresholds in Volts
    "voltage_nominal_min": 350.0,
    "voltage_nominal_max": 420.0,
    "voltage_under": 340.0,
    "voltage_over": 430.0,
    
    # Pack Current thresholds in Amperes (negative = discharge, positive = charge/regen)
    "current_high_discharge": -60.0,
    "current_high_charge": 60.0,
    "current_spike_abs": 75.0,
    
    # Degradation Index threshold (0 - 100 scale)
    "degradation_review_level": 15.0,
    "degradation_high_level": 35.0,
    
    # Health Score thresholds
    "health_critical": 50.0,
    "health_warning": 75.0,
}

SYSTEM_LIMITATIONS = [
    "This report is a decision-support summary and does not replace battery manufacturer guidance or a qualified technician's inspection.",
    "The review thresholds used here are project defaults, not certified manufacturer limits; compare each reading against the operating range specified for this battery pack.",
    "The degradation level is treated as a provided degradation index (0-100); its precise physical meaning is not defined by the current system, so it is not interpreted as a specific percentage of capacity loss."
]
