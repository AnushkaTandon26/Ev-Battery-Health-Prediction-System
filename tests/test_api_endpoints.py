"""
Flask API Integration Tests (10 tests).
Covers prediction route enhancement, report generation, retrieval, and error states.
"""
import unittest
import json
import sys
from pathlib import Path

# Setup paths
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

try:
    from backend.app import app, db
    from backend.database import BatteryData, DiagnosticReport
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False


@unittest.skipUnless(FLASK_AVAILABLE, "Flask or app dependencies unavailable in environment")
class TestReportAPIEndpoints(unittest.TestCase):
    """10 API tests for Flask endpoints and report persistence."""

    def setUp(self):
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.client = app.test_client()

        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_01_api_home_lists_report_routes(self):
        res = self.client.get("/api")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("GET /api/reports", data["endpoints"])
        self.assertIn("POST /api/reports/generate", data["endpoints"])

    def test_02_predict_endpoint_returns_report_additively(self):
        payload = {
            "voltage": 400.0,
            "current": 15.0,
            "soc": 80.0,
            "temp": 28.0,
            "degradation_level": 5.0
        }
        res = self.client.post("/api/predict", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("report", data)
        self.assertEqual(data["report_status"], "generated")
        self.assertIn("summary", data["report"])

    def test_03_predict_persists_battery_and_report(self):
        payload = {"voltage": 390.0, "current": -20.0, "soc": 70.0, "temp": 32.0, "degradation_level": 10.0}
        res = self.client.post("/api/predict", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        record_id = data["record_id"]

        with app.app_context():
            rec = BatteryData.query.get(record_id)
            self.assertIsNotNone(rec)
            rep = DiagnosticReport.query.filter_by(battery_record_id=record_id).first()
            self.assertIsNotNone(rep)
            self.assertEqual(rep.battery_record_id, record_id)

    def test_04_reports_generate_with_telemetry(self):
        body = {
            "telemetry": {"voltage": 360.0, "current": -55.0, "soc": 12.0, "temp": 47.0, "degradation_level": 40.0},
            "generation_method": "context_aware"
        }
        res = self.client.post("/api/reports/generate", json=body)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("summary", data)
        self.assertEqual(data["condition_label"], "Warning")

    def test_05_reports_generate_with_record_id(self):
        with app.app_context():
            rec = BatteryData(voltage=400, current=0, soc=80, temp=25, status="Safe", health_score=92)
            db.session.add(rec)
            db.session.commit()
            rec_id = rec.id

        res = self.client.post("/api/reports/generate", json={"record_id": rec_id})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["battery_record_id"], rec_id)

    def test_06_reports_generate_rejects_missing_payload(self):
        res = self.client.post("/api/reports/generate", json={})
        self.assertEqual(res.status_code, 400)

    def test_07_get_reports_list(self):
        # Insert report
        with app.app_context():
            rep = DiagnosticReport(
                condition_label="Safe",
                health_score=90.0,
                summary="Test summary",
                rendered_text="Test rendered",
                report_data="{}"
            )
            db.session.add(rep)
            db.session.commit()

        res = self.client.get("/api/reports")
        self.assertEqual(res.status_code, 200)
        reports = res.get_json()
        self.assertIsInstance(reports, list)
        self.assertGreaterEqual(len(reports), 1)

    def test_08_get_report_by_id_success(self):
        with app.app_context():
            rep = DiagnosticReport(
                condition_label="Safe",
                health_score=95.0,
                summary="Report 1",
                rendered_text="Report 1 text",
                report_data="{}"
            )
            db.session.add(rep)
            db.session.commit()
            rep_id = rep.id

        res = self.client.get(f"/api/reports/{rep_id}")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["report_id"], rep_id)

    def test_09_get_report_by_id_404(self):
        res = self.client.get("/api/reports/99999")
        self.assertEqual(res.status_code, 404)

    def test_10_get_record_report_by_record_id(self):
        with app.app_context():
            rec = BatteryData(voltage=400, current=0, soc=80, temp=25, status="Safe", health_score=92)
            db.session.add(rec)
            db.session.commit()

            rep = DiagnosticReport(
                battery_record_id=rec.id,
                condition_label="Safe",
                health_score=92.0,
                summary="Linked report",
                rendered_text="Linked text",
                report_data="{}"
            )
            db.session.add(rep)
            db.session.commit()
            rec_id = rec.id

        res = self.client.get(f"/api/records/{rec_id}/report")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["battery_record_id"], rec_id)


if __name__ == "__main__":
    unittest.main()
