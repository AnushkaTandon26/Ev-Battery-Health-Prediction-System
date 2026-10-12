"""Unit tests for the NLG diagnostic pipeline.

Runnable with the Python standard library only (no Flask/TF/sklearn needed):

    python -m unittest discover -s tests -v
    # or
    python tests/test_nlg_pipeline.py

These tests cover validation, fact extraction, rule boundaries, planning,
realization, grounding/safety validation and schema conformance.
"""

import os
import sys
import math
import unittest

# Make backend importable regardless of where tests are run from.
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.join(_HERE, "..", "backend")
sys.path.insert(0, os.path.abspath(_BACKEND))

from nlg.validation import validate_telemetry, validate_prediction, ValidationError  # noqa: E402
from nlg.fact_extractor import build_facts  # noqa: E402
from nlg import diagnostic_rules as rules  # noqa: E402
from nlg.report_generator import generate_report, build_report_object  # noqa: E402
from nlg.report_validator import validate_grounding  # noqa: E402
from nlg.schema import validate_report  # noqa: E402


SAFE_PRED = {"health_score": 88.0, "status": "Safe", "recommendations": [],
             "model_active": True, "model_error": None}


def pred(status="Safe", hs=88.0, active=True, err=None, recs=None):
    return {"health_score": hs, "status": status,
            "recommendations": recs or [], "model_active": active,
            "model_error": err}


class TestValidation(unittest.TestCase):
    def test_valid_telemetry(self):
        norm = validate_telemetry(
            {"voltage": 400, "current": 18, "soc": 83, "temp": 29,
             "degradation_level": 20})
        self.assertEqual(norm["temp"], 29.0)
        self.assertEqual(norm["soc"], 83.0)

    def test_missing_required_strict(self):
        with self.assertRaises(ValidationError):
            validate_telemetry({"voltage": 400}, strict=True)

    def test_nan_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_telemetry({"voltage": 400, "current": 0, "soc": 80,
                                "temp": float("nan")})
        self.assertTrue(any(e["code"] == "NOT_FINITE" for e in ctx.exception.errors))

    def test_infinity_rejected(self):
        with self.assertRaises(ValidationError):
            validate_telemetry({"voltage": 400, "current": 0, "soc": 80,
                                "temp": float("inf")})

    def test_soc_out_of_range(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_telemetry({"voltage": 400, "current": 0, "soc": 150,
                                "temp": 25})
        self.assertTrue(any(e["code"] == "OUT_OF_RANGE" for e in ctx.exception.errors))

    def test_non_numeric_rejected(self):
        with self.assertRaises(ValidationError):
            validate_telemetry({"voltage": "abc", "current": 0, "soc": 80,
                                "temp": 25})

    def test_bool_not_numeric(self):
        with self.assertRaises(ValidationError):
            validate_telemetry({"voltage": True, "current": 0, "soc": 80,
                                "temp": 25})

    def test_non_strict_allows_missing(self):
        norm = validate_telemetry({"soc": 80, "temp": 25}, strict=False)
        self.assertIsNone(norm["degradation_level"])

    def test_validate_prediction_flags_bad_status(self):
        problems = validate_prediction({"health_score": 50, "status": "Weird"})
        self.assertTrue(problems)


class TestRuleBoundaries(unittest.TestCase):
    def _facts(self, **tel):
        base = {"voltage": 400, "current": 0, "soc": 80, "temperature": 25,
                "degradation_level": 0}
        base.update(tel)
        return build_facts(base, SAFE_PRED, record_id=1)

    def test_temp_below_review_no_finding(self):
        f = self._facts(temperature=34.9)
        self.assertIsNone(rules.rule_temperature(f))

    def test_temp_at_review_medium(self):
        f = self._facts(temperature=35.0)
        self.assertEqual(rules.rule_temperature(f).severity, "medium")

    def test_temp_at_critical(self):
        f = self._facts(temperature=45.0)
        self.assertEqual(rules.rule_temperature(f).severity, "critical")

    def test_soc_low_boundary(self):
        self.assertIsNone(rules.rule_low_soc(self._facts(soc=20.1)))
        self.assertEqual(rules.rule_low_soc(self._facts(soc=20.0)).severity, "medium")
        self.assertEqual(rules.rule_low_soc(self._facts(soc=10.0)).severity, "high")

    def test_current_boundaries(self):
        self.assertIsNone(rules.rule_high_current(self._facts(current=44.9)))
        self.assertEqual(rules.rule_high_current(self._facts(current=-50)).severity, "high")

    def test_degradation_bands(self):
        self.assertIsNone(rules.rule_degradation(self._facts(degradation_level=14.9)))
        self.assertEqual(rules.rule_degradation(self._facts(degradation_level=15)).severity, "low")
        self.assertEqual(rules.rule_degradation(self._facts(degradation_level=35)).severity, "high")

    def test_multiple_concerns_sorted(self):
        f = self._facts(temperature=47, soc=8, current=60, degradation_level=40)
        findings = rules.evaluate(f)
        severities = [x.severity for x in findings]
        # critical/high should come before medium/low
        weights = [rules._SEVERITY_WEIGHT[s] for s in severities]
        self.assertEqual(weights, sorted(weights, reverse=True))

    def test_no_findings_when_normal(self):
        f = self._facts()
        # health 88 safe, everything nominal
        self.assertEqual(rules.evaluate(f), [])


class TestTrendAndConflicts(unittest.TestCase):
    def test_no_trend_with_one_record(self):
        f = build_facts({"voltage": 400, "current": 0, "soc": 80,
                         "temperature": 25, "degradation_level": 0},
                        SAFE_PRED, record_id=2,
                        recent_records=[{"health_score": 80}])
        self.assertIsNone(f.trend)

    def test_trend_detected(self):
        recs = [{"health_score": 90}, {"health_score": 80}, {"health_score": 70}]
        f = build_facts({"voltage": 400, "current": 0, "soc": 80,
                         "temperature": 25, "degradation_level": 0},
                        SAFE_PRED, record_id=3, recent_records=recs)
        self.assertIsNotNone(f.trend)
        self.assertGreaterEqual(f.trend.health_drop_pct, 10)

    def test_conflict_safe_but_critical(self):
        # Force a critical temperature while status says Safe.
        f = build_facts({"voltage": 400, "current": 0, "soc": 80,
                         "temperature": 50, "degradation_level": 0},
                        pred(status="Safe", hs=90), record_id=4)
        findings = rules.evaluate(f)
        conflicts = rules.detect_conflicts(f, findings)
        self.assertTrue(any("Safe" in c for c in conflicts))


class TestReportGeneration(unittest.TestCase):
    def test_safe_report_schema_valid(self):
        env = generate_report(
            {"voltage": 400, "current": 18, "soc": 83, "temperature": 29,
             "degradation_level": 5},
            pred(status="Safe", hs=88), record_id=10)
        self.assertEqual(env["report_status"], "generated")
        self.assertEqual(env["schema_errors"], [])
        self.assertEqual(env["grounding_errors"], [])

    def test_critical_report(self):
        env = generate_report(
            {"voltage": 360, "current": -55, "soc": 12, "temperature": 47,
             "degradation_level": 40},
            pred(status="Critical", hs=33, active=False, err="TF missing"),
            record_id=11)
        self.assertEqual(env["report_status"], "generated")
        self.assertEqual(env["report"]["model_status"], "fallback")
        self.assertEqual(env["report"]["overall_status"], "Critical")
        codes = {f["code"] for f in env["report"]["findings"]}
        self.assertIn("TEMPERATURE_HIGH", codes)
        self.assertIn("SOC_LOW", codes)

    def test_fallback_disclosed(self):
        env = generate_report(
            {"voltage": 400, "current": 10, "soc": 80, "temperature": 25,
             "degradation_level": 0},
            pred(active=False, err="TF missing"), record_id=12)
        lims = " ".join(env["report"]["limitations"]).lower()
        self.assertIn("fallback", lims)

    def test_source_snapshot_matches(self):
        env = generate_report(
            {"voltage": 401.5, "current": 12.25, "soc": 72, "temperature": 31,
             "degradation_level": 8},
            pred(status="Safe", hs=86.4), record_id=13)
        snap = env["report"]["source_snapshot"]
        self.assertEqual(snap["voltage"], 401.5)
        self.assertEqual(snap["temp"], 31)
        self.assertEqual(snap["health_score"], 86.4)

    def test_missing_degradation_marked(self):
        env = generate_report(
            {"voltage": 400, "current": 10, "soc": 80, "temperature": 25},
            pred(status="Safe", hs=85), record_id=14)
        self.assertIsNone(env["report"]["source_snapshot"]["degradation_level"])

    def test_recommendations_traceable(self):
        env = generate_report(
            {"voltage": 360, "current": 10, "soc": 15, "temperature": 42,
             "degradation_level": 0},
            pred(status="Warning", hs=60), record_id=15)
        finding_codes = {f["code"] for f in env["report"]["findings"]}
        for rec in env["report"]["recommendations"]:
            if rec["source"] == "rule":
                self.assertTrue(set(rec["related_finding_codes"]).issubset(finding_codes))


class TestSafetyValidator(unittest.TestCase):
    def test_rejects_unsafe_phrase(self):
        f = build_facts({"voltage": 400, "current": 0, "soc": 80,
                         "temperature": 25, "degradation_level": 0},
                        SAFE_PRED, record_id=20)
        report = build_report_object(f)
        payload = {k: v for k, v in report.items() if not k.startswith("_")}
        payload["summary"] = "The battery is safe to drive and the fault is confirmed."
        errors = validate_grounding(payload, f)
        self.assertTrue(any("unsafe" in e for e in errors))

    def test_rejects_fabricated_number(self):
        f = build_facts({"voltage": 400, "current": 0, "soc": 80,
                         "temperature": 25, "degradation_level": 0},
                        SAFE_PRED, record_id=21)
        report = build_report_object(f)
        payload = {k: v for k, v in report.items() if not k.startswith("_")}
        payload["source_snapshot"]["voltage"] = 999.0  # tamper
        errors = validate_grounding(payload, f)
        self.assertTrue(any("voltage" in e for e in errors))


class TestSchemaFallback(unittest.TestCase):
    def test_schema_rejects_bad_report(self):
        errors = validate_report({"schema_version": "1.0"})  # missing most keys
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
