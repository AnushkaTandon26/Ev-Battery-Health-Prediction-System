"""
Unit tests for the NLG subsystem (29 tests).
Covers validation, fact extraction, diagnostic rules, content planning,
sentence realization, report grounding/validation, and schema compliance.
"""
import unittest
import math
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from backend.nlg.validation import validate_and_normalize_inputs, ValidationError
from backend.nlg.fact_extractor import extract_diagnostic_facts, DiagnosticFact
from backend.nlg.diagnostic_rules import evaluate_diagnostic_rules, DiagnosticFinding
from backend.nlg.report_planner import plan_report_content
from backend.nlg.sentence_realizer import (
    realize_baseline_text,
    realize_context_aware_text,
    realize_sentences
)
from backend.nlg.report_validator import (
    validate_grounding_and_fidelity,
    validate_complete_report
)
from backend.nlg.schema import validate_report_schema
from backend.nlg.report_generator import generate_diagnostic_report


class TestNLGValidation(unittest.TestCase):
    """Tests 1-5: Input validation and domain checks."""

    def test_01_valid_telemetry_accepted(self):
        telemetry = {"voltage": 400.0, "current": 10.0, "soc": 80.0, "temp": 25.0, "degradation_level": 5.0}
        clean_tel, clean_pred = validate_and_normalize_inputs(telemetry)
        self.assertEqual(clean_tel["voltage"], 400.0)
        self.assertEqual(clean_tel["soc"], 80.0)

    def test_02_reject_non_numeric_input(self):
        telemetry = {"voltage": "invalid_val", "current": 10.0, "soc": 80.0, "temp": 25.0}
        with self.assertRaises(ValidationError):
            validate_and_normalize_inputs(telemetry)

    def test_03_reject_nan_and_inf(self):
        telemetry = {"voltage": float("nan"), "current": 10.0, "soc": 80.0, "temp": 25.0}
        with self.assertRaises(ValidationError):
            validate_and_normalize_inputs(telemetry)

    def test_04_reject_out_of_domain_voltage(self):
        telemetry = {"voltage": 50.0, "current": 10.0, "soc": 80.0, "temp": 25.0}
        with self.assertRaises(ValidationError):
            validate_and_normalize_inputs(telemetry)

    def test_05_reject_out_of_domain_soc(self):
        telemetry = {"voltage": 400.0, "current": 10.0, "soc": 115.0, "temp": 25.0}
        with self.assertRaises(ValidationError):
            validate_and_normalize_inputs(telemetry)


class TestNLGFactExtraction(unittest.TestCase):
    """Tests 6-9: Structured fact extraction."""

    def setUp(self):
        self.telemetry = {"voltage": 400.0, "current": 20.0, "soc": 75.0, "temp": 30.0, "degradation_level": 10.0}
        self.prediction = {"health_score": 90.0, "status": "Safe", "model_active": True}

    def test_06_extracts_all_measurement_facts(self):
        facts = extract_diagnostic_facts(self.telemetry, self.prediction)
        params = {f.parameter for f in facts if f.category == "measurement"}
        self.assertTrue({"voltage", "current", "soc", "temp", "degradation_level"}.issubset(params))

    def test_07_computes_derived_pack_power(self):
        facts = extract_diagnostic_facts(self.telemetry, self.prediction)
        power_fact = next(f for f in facts if f.parameter == "pack_power")
        self.assertEqual(power_fact.value, 8000.0)
        self.assertEqual(power_fact.unit, "W")

    def test_08_extracts_prediction_facts_with_provenance(self):
        facts = extract_diagnostic_facts(self.telemetry, self.prediction)
        hs_fact = next(f for f in facts if f.parameter == "health_score")
        self.assertEqual(hs_fact.value, 90.0)
        self.assertEqual(hs_fact.source, "keras_model")

    def test_09_extracts_recommendation_facts(self):
        plan = {"recommended_actions": [{"action": "Check cell balance", "priority": "high"}]}
        facts = extract_diagnostic_facts(self.telemetry, self.prediction, maintenance_plan=plan)
        rec_facts = [f for f in facts if f.category == "recommendation"]
        self.assertTrue(len(rec_facts) >= 1)
        self.assertIn("Check cell balance", rec_facts[0].value)


class TestNLGDiagnosticRules(unittest.TestCase):
    """Tests 10-15: Rule engine evaluation."""

    def test_10_high_temperature_warning(self):
        facts = [
            DiagnosticFact("1", "measurement", "temp", 45.0, "°C"),
            DiagnosticFact("2", "measurement", "soc", 80.0, "%")
        ]
        findings = evaluate_diagnostic_rules(facts)
        rule_ids = [f.rule_id for f in findings]
        self.assertIn("RULE_TEMP_HIGH", rule_ids)

    def test_11_critical_temperature_alert(self):
        facts = [DiagnosticFact("1", "measurement", "temp", 50.0, "°C")]
        findings = evaluate_diagnostic_rules(facts)
        critical_f = next(f for f in findings if f.rule_id == "RULE_TEMP_CRITICAL")
        self.assertEqual(critical_f.severity, "Critical")

    def test_12_low_soc_warning(self):
        facts = [DiagnosticFact("1", "measurement", "soc", 18.0, "%")]
        findings = evaluate_diagnostic_rules(facts)
        rule_ids = [f.rule_id for f in findings]
        self.assertIn("RULE_SOC_LOW", rule_ids)

    def test_13_critical_low_soc(self):
        facts = [DiagnosticFact("1", "measurement", "soc", 10.0, "%")]
        findings = evaluate_diagnostic_rules(facts)
        rule_ids = [f.rule_id for f in findings]
        self.assertIn("RULE_SOC_CRITICAL_LOW", rule_ids)

    def test_14_high_current_discharge(self):
        facts = [DiagnosticFact("1", "measurement", "current", -70.0, "A")]
        findings = evaluate_diagnostic_rules(facts)
        rule_ids = [f.rule_id for f in findings]
        self.assertIn("RULE_CURRENT_HIGH_DISCHARGE", rule_ids)

    def test_15_degradation_index_elevated(self):
        facts = [DiagnosticFact("1", "measurement", "degradation_level", 20.0, "%")]
        findings = evaluate_diagnostic_rules(facts)
        rule_ids = [f.rule_id for f in findings]
        self.assertIn("RULE_DEGRADATION_ELEVATED", rule_ids)


class TestNLGReportPlanner(unittest.TestCase):
    """Tests 16-19: Content planning and ordering."""

    def test_16_sorts_findings_by_severity(self):
        facts = [
            DiagnosticFact("1", "measurement", "temp", 50.0, "°C"),
            DiagnosticFact("2", "measurement", "degradation_level", 20.0, "%")
        ]
        findings = [
            DiagnosticFinding("RULE_DEGRADATION_ELEVATED", "Low", "Degradation", "desc", "degradation_level", 20.0),
            DiagnosticFinding("RULE_TEMP_CRITICAL", "Critical", "Temp Critical", "desc", "temp", 50.0)
        ]
        plan = plan_report_content(facts, findings)
        self.assertEqual(plan.prioritized_findings[0].severity, "Critical")
        self.assertEqual(plan.prioritized_findings[1].severity, "Low")

    def test_17_promotes_condition_to_critical_if_critical_finding_present(self):
        facts = [DiagnosticFact("1", "prediction", "status", "Safe")]
        findings = [DiagnosticFinding("RULE_TEMP_CRITICAL", "Critical", "Temp", "desc", "temp", 52.0)]
        plan = plan_report_content(facts, findings)
        self.assertEqual(plan.condition_label, "Critical")

    def test_18_deduplicates_duplicate_rules(self):
        facts = []
        findings = [
            DiagnosticFinding("RULE_TEMP_HIGH", "High", "Temp High 1", "desc", "temp", 44.0),
            DiagnosticFinding("RULE_TEMP_HIGH", "High", "Temp High 2", "desc", "temp", 44.0)
        ]
        plan = plan_report_content(facts, findings)
        self.assertEqual(len(plan.prioritized_findings), 1)

    def test_19_prioritizes_actions(self):
        facts = [
            DiagnosticFact("1", "recommendation", "rec", "Routine check", source="planner"),
            DiagnosticFact("2", "recommendation", "rec", "Replace cooling pump immediately", source="planner")
        ]
        plan = plan_report_content(facts, [])
        self.assertEqual(plan.prioritized_actions[0]["priority"], "high")


class TestNLGSentenceRealizer(unittest.TestCase):
    """Tests 20-23: Text realization (baseline and context-aware)."""

    def setUp(self):
        facts = [
            DiagnosticFact("1", "measurement", "voltage", 400.0, "V"),
            DiagnosticFact("2", "prediction", "health_score", 92.7, "%"),
            DiagnosticFact("3", "prediction", "status", "Safe")
        ]
        self.plan = plan_report_content(facts, [])

    def test_20_baseline_realizer_produces_structured_text(self):
        out = realize_baseline_text(self.plan)
        self.assertIn("SUMMARY", out["rendered_text"])
        self.assertIn("92.7%", out["summary"])

    def test_21_context_aware_realizer_includes_provenance(self):
        out = realize_context_aware_text(self.plan)
        self.assertIn("fallback heuristic", out["summary"])

    def test_22_context_aware_model_active_provenance(self):
        self.plan.model_active = True
        out = realize_context_aware_text(self.plan)
        self.assertIn("machine learning sequence model", out["summary"])

    def test_23_realize_sentences_dispatch(self):
        base = realize_sentences(self.plan, method="baseline")
        ctx = realize_sentences(self.plan, method="context_aware")
        self.assertNotEqual(base["summary"], ctx["summary"])


class TestNLGReportValidatorAndSchema(unittest.TestCase):
    """Tests 24-29: Grounding, fidelity, and schema verification."""

    def setUp(self):
        self.telemetry = {"voltage": 395.0, "current": -15.0, "soc": 82.0, "temp": 28.0, "degradation_level": 5.0}
        self.prediction = {"health_score": 91.5, "status": "Safe"}

    def test_24_end_to_end_report_generation(self):
        report = generate_diagnostic_report(self.telemetry, self.prediction)
        self.assertIn("summary", report)
        self.assertEqual(report["condition_label"], "Safe")
        self.assertEqual(report["health_score"], 91.5)

    def test_25_schema_validation_passes_valid_report(self):
        report = generate_diagnostic_report(self.telemetry, self.prediction)
        is_valid, errors = validate_report_schema(report)
        self.assertTrue(is_valid, f"Schema validation failed: {errors}")

    def test_26_schema_validation_rejects_missing_required_field(self):
        report = generate_diagnostic_report(self.telemetry, self.prediction)
        del report["summary"]
        is_valid, errors = validate_report_schema(report)
        self.assertFalse(is_valid)

    def test_27_grounding_rejects_mismatched_health_score(self):
        report = generate_diagnostic_report(self.telemetry, self.prediction)
        report["health_score"] = 45.0  # Mismatch from source 91.5
        is_valid, errors = validate_grounding_and_fidelity(report, self.telemetry, self.prediction)
        self.assertFalse(is_valid)
        self.assertTrue(any("Health score mismatch" in e for e in errors))

    def test_28_grounding_rejects_unsupported_claim(self):
        report = generate_diagnostic_report(self.telemetry, self.prediction)
        report["summary"] += " Internal short circuit verified by AI."
        is_valid, errors = validate_grounding_and_fidelity(report, self.telemetry, self.prediction)
        self.assertFalse(is_valid)
        self.assertTrue(any("unsupported diagnostic claim" in e for e in errors))

    def test_29_validate_complete_report_composite(self):
        report = generate_diagnostic_report(self.telemetry, self.prediction)
        is_ok, errs = validate_complete_report(report, self.telemetry, self.prediction)
        self.assertTrue(is_ok, f"Validation errors: {errs}")


if __name__ == "__main__":
    unittest.main()
