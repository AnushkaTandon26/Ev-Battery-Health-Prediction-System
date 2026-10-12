"""API / integration tests for the Flask app and DiagnosticReport persistence.

These require Flask + Flask-SQLAlchemy. When those are not installed the whole
module is skipped (so the pure-NLG unit tests still run anywhere). Uses an
in-memory SQLite database so it never touches the real instance DB.

    python -m unittest tests.test_api -v
"""

import os
import sys
import json
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.abspath(os.path.join(_HERE, "..", "backend"))
sys.path.insert(0, _BACKEND)

try:
    import flask  # noqa: F401
    import flask_sqlalchemy  # noqa: F401
    _HAVE_FLASK = True
except Exception:
    _HAVE_FLASK = False


@unittest.skipUnless(_HAVE_FLASK, "Flask / Flask-SQLAlchemy not installed")
class TestApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Import inside the guard so collection never fails without Flask.
        os.chdir(_BACKEND)
        import importlib
        app_module = importlib.import_module("app")
        cls.app_module = app_module
        app = app_module.app
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        cls.db = app_module.db
        with app.app_context():
            cls.db.create_all()
            app_module.ensure_schema()
        cls.client = app.test_client()
        cls.app = app

    def _predict(self, **override):
        payload = {"voltage": 400, "current": 18, "soc": 83, "temp": 29,
                   "degradation_level": 20}
        payload.update(override)
        return self.client.post("/api/predict", json=payload)

    def test_predict_returns_report(self):
        resp = self._predict()
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        # Existing contract preserved.
        for key in ("health_score", "status", "recommendations",
                    "record_id", "agent_plan", "model_active"):
            self.assertIn(key, data)
        # New additive fields.
        self.assertIn("report_status", data)
        self.assertIn("diagnostic_report", data)

    def test_predict_rejects_nan(self):
        resp = self.client.post("/api/predict",
                                json={"voltage": 400, "current": 0,
                                      "soc": 80, "temp": float("nan")})
        # Flask/json may not accept NaN; accept either a 422 or 400.
        self.assertIn(resp.status_code, (400, 422))

    def test_predict_rejects_out_of_range_soc(self):
        resp = self._predict(soc=150)
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.get_json()["error"]["code"], "VALIDATION_ERROR")

    def test_report_persist_and_fetch(self):
        resp = self._predict()
        report = resp.get_json()["diagnostic_report"]
        self.assertIsNotNone(report)
        rid = report["report_id"]
        got = self.client.get(f"/api/reports/{rid}")
        self.assertEqual(got.status_code, 200)
        self.assertEqual(got.get_json()["report"]["report_id"], rid)

    def test_unknown_report_404(self):
        self.assertEqual(self.client.get("/api/reports/999999").status_code, 404)

    def test_generate_report_from_record(self):
        rec_id = self._predict().get_json()["record_id"]
        resp = self.client.post("/api/reports/generate", json={"record_id": rec_id})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.get_json()["battery_record_id"], rec_id)

    def test_generate_report_unknown_record_404(self):
        resp = self.client.post("/api/reports/generate", json={"record_id": 999999})
        self.assertEqual(resp.status_code, 404)

    def test_generate_report_missing_id_400(self):
        resp = self.client.post("/api/reports/generate", json={})
        self.assertEqual(resp.status_code, 400)

    def test_list_reports(self):
        self._predict()
        resp = self.client.get("/api/reports?limit=5")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json(), list)

    def test_existing_endpoints_intact(self):
        self._predict()
        for url in ("/api/history", "/api/stats", "/api/detailed-stats",
                    "/api/agent/tasks"):
            self.assertEqual(self.client.get(url).status_code, 200, url)


if __name__ == "__main__":
    unittest.main(verbosity=2)
