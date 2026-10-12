from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os

from agentic_ai import build_maintenance_plan
from database import db, BatteryData, MaintenanceTask, DiagnosticReport, ensure_schema
from utils import predict_battery_health
from report_service import generate_and_store
from nlg.validation import validate_telemetry, ValidationError

app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../instance/ev_battery.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Secret key and debug flag come from the environment so production secrets are
# never committed (TRD section 12). A dev default keeps local use frictionless.
app.secret_key = os.environ.get("EV_SECRET_KEY", "ev-battery-dev-secret-change-me")

CORS(app)
db.init_app(app)

with app.app_context():
    db.create_all()
    ensure_schema()

# ==================== STATIC FILES ====================
@app.route("/")
def index():
    return send_from_directory('../frontend', 'index.html')

@app.route("/<path:filename>")
def serve_static(filename):
    try:
        return send_from_directory('../frontend', filename)
    except:
        return send_from_directory('../frontend', 'index.html')


# ==================== API HOME ====================
@app.route("/api")
def api_home():
    return jsonify({
        "message": "EV Battery Health Prediction API",
        "endpoints": {
            "POST /api/predict": "Make prediction & save (now also returns diagnostic_report)",
            "GET /api/history": "Recent predictions",
            "GET /api/stats": "System stats",
            "GET /api/detailed-stats": "Detailed statistics",
            "GET /api/agent/tasks": "Autonomous maintenance tasks",
            "POST /api/reports/generate": "Generate a diagnostic report for a saved record",
            "GET /api/reports": "List diagnostic reports (newest first)",
            "GET /api/reports/<report_id>": "Fetch one diagnostic report",
            "GET /api/records/<record_id>/report": "Latest report for a battery record"
        },
        "status": "running"
    })

# ==================== AUTHENTICATION ====================
# Authentication endpoints removed - direct access to dashboard

# ==================== ERROR HELPER ====================
def _error_response(code, message, status, details=None):
    """Consistent JSON error envelope (BACKEND_SCHEMA section 8)."""
    return jsonify({
        "error": {"code": code, "message": message, "details": details or {}}
    }), status

# ==================== PREDICTION ENDPOINTS ====================
@app.route("/api/predict", methods=["POST"])
def predict():
    try:
        data = request.json
        if not isinstance(data, dict):
            return _error_response(
                "INVALID_REQUEST", "Request body must be a JSON object.", 400)

        # Validate any values that ARE present (non-strict preserves the
        # legacy default behaviour below for absent fields, per BACKEND_SCHEMA
        # compatibility note). Rejects NaN/inf/out-of-range values with 422.
        try:
            validate_telemetry(data, strict=False)
        except ValidationError as ve:
            return _error_response(
                "VALIDATION_ERROR", "One or more telemetry values are invalid.",
                422, details={"errors": ve.errors})

        voltage = float(data.get("voltage", 400))
        current = float(data.get("current", 0))
        soc = float(data.get("soc", 80))
        temp = float(data.get("temp", 25))
        degradation_level = float(data.get("degradation_level", 0))

        recent_records = BatteryData.query.order_by(BatteryData.timestamp.desc()).limit(127).all()
        recent_records = [record.to_dict() for record in reversed(recent_records)]

        # Get ML prediction
        prediction = predict_battery_health(
            voltage,
            current,
            soc,
            temp,
            degradation_level=degradation_level,
            recent_records=recent_records
        )
        maintenance_plan = build_maintenance_plan(
            prediction,
            {
                "voltage": voltage,
                "current": current,
                "soc": soc,
                "temp": temp,
                "degradation_level": degradation_level
            },
            recent_records=recent_records
        )

        # Save to database
        battery_record = BatteryData(
            voltage=voltage,
            current=current,
            soc=soc,
            temp=temp,
            degradation_level=degradation_level,
            status=prediction["status"],
            health_score=prediction["health_score"]
        )
        db.session.add(battery_record)
        db.session.flush()

        maintenance_task = MaintenanceTask(
            battery_record_id=battery_record.id,
            task_type=maintenance_plan["task_type"],
            priority=maintenance_plan["priority"],
            title=maintenance_plan["title"],
            summary=maintenance_plan["summary"],
            action_status=maintenance_plan["action_status"],
            execution_mode=maintenance_plan["execution_mode"],
            assigned_team=maintenance_plan["assigned_team"],
            scheduled_for=maintenance_plan["scheduled_for"],
            recommended_actions=json.dumps(maintenance_plan["recommended_actions"]),
            automation_notes=maintenance_plan["automation_notes"]
        )
        db.session.add(maintenance_task)
        # Commit the authoritative prediction + plan FIRST so a later report
        # failure can never roll them back.
        db.session.commit()

        # Report generation is isolated: a failure here keeps the prediction.
        diagnostic_report = None
        report_status = "failed"
        report_error_code = None
        try:
            telemetry = {
                "voltage": voltage, "current": current, "soc": soc,
                "temp": temp, "degradation_level": degradation_level,
            }
            row, envelope = generate_and_store(
                db, DiagnosticReport, battery_record.id, telemetry, prediction,
                recent_records=recent_records, maintenance_plan=maintenance_plan)
            report_status = envelope["report_status"]
            if row is not None:
                diagnostic_report = row.to_dict()["report"]
            else:
                report_error_code = (envelope.get("error")
                                     or "REPORT_VALIDATION_FAILED")
        except Exception as report_exc:  # noqa: BLE001 - never break prediction
            db.session.rollback()
            report_status = "failed"
            report_error_code = f"{type(report_exc).__name__}"

        return jsonify({
            "health_score": prediction["health_score"],
            "status": prediction["status"],
            "recommendations": prediction["recommendations"],
            "degradation_level": prediction.get("degradation_level"),
            "record_id": battery_record.id,
            "agent_plan": {
                **maintenance_task.to_dict(),
                "schedule_label": maintenance_plan["schedule_label"]
            },
            "model_active": prediction.get("model_active", False),
            "model_error": prediction.get("model_error"),
            "report_status": report_status,
            "report_error_code": report_error_code,
            "diagnostic_report": diagnostic_report
        }), 200
    except Exception as e:
        db.session.rollback()
        return _error_response("INTERNAL_ERROR", "Prediction processing failed.", 500)

# ==================== HISTORY ENDPOINTS ====================
@app.route("/api/history", methods=["GET"])
def history():
    try:
        limit = request.args.get("limit", 50, type=int)
        records = BatteryData.query.order_by(BatteryData.timestamp.desc()).limit(limit).all()
        return jsonify([r.to_dict() for r in records]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/agent/tasks", methods=["GET"])
def agent_tasks():
    try:
        limit = request.args.get("limit", 10, type=int)
        tasks = MaintenanceTask.query.order_by(MaintenanceTask.created_at.desc()).limit(limit).all()
        return jsonify([task.to_dict() for task in tasks]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== STATS ENDPOINTS ====================
@app.route("/api/stats", methods=["GET"])
def stats():
    try:
        total_records = BatteryData.query.count()
        critical_count = BatteryData.query.filter_by(status="Critical").count()
        warning_count = BatteryData.query.filter_by(status="Warning").count()
        safe_count = BatteryData.query.filter_by(status="Safe").count()
        
        avg_health = 85
        if total_records > 0:
            avg_health = db.session.query(db.func.avg(BatteryData.health_score)).scalar() or 85
        
        return jsonify({
            "total_records": total_records,
            "critical_count": critical_count,
            "warning_count": warning_count,
            "safe_count": safe_count,
            "average_health": round(avg_health, 2)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/detailed-stats", methods=["GET"])
def detailed_stats():
    try:
        records = BatteryData.query.order_by(BatteryData.timestamp.desc()).limit(100).all()
        
        if not records:
            return jsonify({
                "avg_voltage": 400,
                "avg_current": 0,
                "avg_soc": 80,
                "avg_temp": 25,
                "avg_degradation": 0,
                "avg_health": 85,
                "records": []
            }), 200
        
        voltages = [r.voltage for r in records]
        currents = [r.current for r in records]
        socs = [r.soc for r in records]
        temps = [r.temp for r in records]
        degradations = [r.degradation_level or 0 for r in records]
        healths = [r.health_score for r in records]
        
        return jsonify({
            "avg_voltage": round(sum(voltages) / len(voltages), 2),
            "avg_current": round(sum(currents) / len(currents), 2),
            "avg_soc": round(sum(socs) / len(socs), 2),
            "avg_temp": round(sum(temps) / len(temps), 2),
            "avg_degradation": round(sum(degradations) / len(degradations), 2),
            "avg_health": round(sum(healths) / len(healths), 2),
            "records": [r.to_dict() for r in records]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== DIAGNOSTIC REPORT ENDPOINTS ====================
@app.route("/api/reports/generate", methods=["POST"])
def generate_report_endpoint():
    """Generate (or re-generate) a diagnostic report for a saved record.

    Does NOT rerun the predictor: it reuses the persisted prediction values and
    the latest maintenance task for that record.
    """
    try:
        data = request.json or {}
        record_id = data.get("record_id")
        if record_id is None:
            return _error_response(
                "INVALID_REPORT_REQUEST", "A valid saved record_id is required.", 400)

        record = BatteryData.query.get(record_id)
        if record is None:
            return _error_response(
                "RECORD_NOT_FOUND", f"No battery record with id {record_id}.", 404)

        # Rebuild the prediction shape from the persisted record (no re-predict).
        prediction = {
            "health_score": record.health_score,
            "status": record.status,
            "recommendations": [],
            "degradation_level": record.degradation_level,
            # Persisted records don't store model metadata; mark unknown.
            "model_active": False,
            "model_error": None,
        }
        telemetry = {
            "voltage": record.voltage, "current": record.current,
            "soc": record.soc, "temp": record.temp,
            "degradation_level": record.degradation_level,
        }

        task = (MaintenanceTask.query
                .filter_by(battery_record_id=record.id)
                .order_by(MaintenanceTask.created_at.desc()).first())
        maintenance_plan = None
        if task is not None:
            maintenance_plan = {
                "priority": task.priority, "title": task.title,
                "recommended_actions": task.to_dict()["recommended_actions"],
            }

        # recent records up to this one, for trend context
        recent = (BatteryData.query
                  .filter(BatteryData.id <= record.id)
                  .order_by(BatteryData.timestamp.desc()).limit(127).all())
        recent = [r.to_dict() for r in reversed(recent)]

        row, envelope = generate_and_store(
            db, DiagnosticReport, record.id, telemetry, prediction,
            recent_records=recent, maintenance_plan=maintenance_plan)

        if row is None:
            return _error_response(
                "REPORT_GENERATION_FAILED",
                "The report could not be generated from the stored record.",
                422, details={"reason": envelope.get("error"),
                              "schema_errors": envelope.get("schema_errors"),
                              "grounding_errors": envelope.get("grounding_errors")})

        return jsonify(row.to_dict()), 201
    except Exception:
        db.session.rollback()
        return _error_response("INTERNAL_ERROR", "Report generation failed.", 500)


@app.route("/api/reports", methods=["GET"])
def list_reports():
    try:
        limit = request.args.get("limit", 20, type=int)
        limit = max(1, min(limit, 100))  # bound the read
        rows = (DiagnosticReport.query
                .order_by(DiagnosticReport.created_at.desc()).limit(limit).all())
        return jsonify([r.to_dict(include_full=False) for r in rows]), 200
    except Exception:
        return _error_response("INTERNAL_ERROR", "Could not list reports.", 500)


@app.route("/api/reports/<int:report_id>", methods=["GET"])
def get_report(report_id):
    try:
        row = DiagnosticReport.query.get(report_id)
        if row is None:
            return _error_response(
                "REPORT_NOT_FOUND", f"No report with id {report_id}.", 404)
        return jsonify(row.to_dict()), 200
    except Exception:
        return _error_response("INTERNAL_ERROR", "Could not fetch report.", 500)


@app.route("/api/records/<int:record_id>/report", methods=["GET"])
def get_record_report(record_id):
    try:
        row = (DiagnosticReport.query
               .filter_by(battery_record_id=record_id)
               .order_by(DiagnosticReport.created_at.desc()).first())
        if row is None:
            return _error_response(
                "REPORT_NOT_FOUND",
                f"No report for battery record {record_id}.", 404)
        return jsonify(row.to_dict()), 200
    except Exception:
        return _error_response("INTERNAL_ERROR", "Could not fetch report.", 500)

# ==================== ERROR HANDLERS ====================
@app.errorhandler(404)
def not_found(error):
    return send_from_directory('../frontend', 'index.html')

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    debug_mode = os.environ.get("EV_DEBUG", "0") == "1"
    app.run(debug=debug_mode, use_reloader=False, host='0.0.0.0', port=5000, threaded=True)
