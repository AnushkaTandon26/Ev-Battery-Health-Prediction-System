from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
root_dir = backend_dir.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

try:
    from backend.database import db, BatteryData, MaintenanceTask, DiagnosticReport, ensure_schema
    from backend.agentic_ai import build_maintenance_plan
    from backend.utils import predict_battery_health
    from backend.report_service import (
        create_and_persist_report,
        get_recent_reports,
        get_report_by_id,
        get_report_by_record_id
    )
    from backend.nlg.report_generator import generate_diagnostic_report
except ImportError:
    from database import db, BatteryData, MaintenanceTask, DiagnosticReport, ensure_schema
    from agentic_ai import build_maintenance_plan
    from utils import predict_battery_health
    from report_service import (
        create_and_persist_report,
        get_recent_reports,
        get_report_by_id,
        get_report_by_record_id
    )
    from nlg.report_generator import generate_diagnostic_report

FRONTEND_DIR = str(root_dir / 'frontend')
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')

import os
if os.environ.get("VERCEL"):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/ev_battery.db'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../instance/ev_battery.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'ev-battery-secret-2024-change-in-production'

CORS(app)
db.init_app(app)

with app.app_context():
    db.create_all()
    ensure_schema()

# ==================== STATIC FILES ====================
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route("/<path:filename>")
def serve_static(filename):
    try:
        return send_from_directory(FRONTEND_DIR, filename)
    except Exception:
        return send_from_directory(FRONTEND_DIR, 'index.html')


# ==================== API HOME ====================
@app.route("/api")
def api_home():
    return jsonify({
        "message": "EV Battery Health Prediction & NLG Diagnostic Reporting API",
        "endpoints": {
            "POST /api/predict": "Make prediction, generate maintenance plan & diagnostic report",
            "POST /api/reports/generate": "Generate or persist on-demand diagnostic report",
            "GET /api/reports": "Recent diagnostic reports",
            "GET /api/reports/<report_id>": "Specific diagnostic report by ID",
            "GET /api/records/<record_id>/report": "Diagnostic report for a specific battery record",
            "GET /api/history": "Recent predictions",
            "GET /api/stats": "System stats",
            "GET /api/detailed-stats": "Detailed statistics",
            "GET /api/agent/tasks": "Autonomous maintenance tasks"
        },
        "status": "running"
    })

# ==================== AUTHENTICATION ====================
# Authentication endpoints removed - direct access to dashboard

# ==================== PREDICTION ENDPOINTS ====================
@app.route("/api/predict", methods=["POST"])
def predict():
    try:
        data = request.json or {}
        
        voltage = float(data.get("voltage", 400))
        current = float(data.get("current", 0))
        soc = float(data.get("soc", 80))
        temp = float(data.get("temp", 25))
        degradation_level = float(data.get("degradation_level", 0))
        generation_method = data.get("generation_method", "context_aware")

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
        
        # Generate and persist Diagnostic Report
        diagnostic_report = None
        report_status = "none"
        try:
            diagnostic_report = create_and_persist_report(
                telemetry={
                    "voltage": voltage,
                    "current": current,
                    "soc": soc,
                    "temp": temp,
                    "degradation_level": degradation_level
                },
                prediction=prediction,
                maintenance_plan=maintenance_plan,
                battery_record_id=battery_record.id,
                generation_method=generation_method
            )
            report_status = "generated"
        except Exception as nlg_err:
            report_status = f"failed: {str(nlg_err)}"

        db.session.commit()
        
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
            "report": diagnostic_report
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== REPORT ENDPOINTS ====================
@app.route("/api/reports/generate", methods=["POST"])
def generate_report_endpoint():
    try:
        data = request.json or {}
        telemetry = data.get("telemetry")
        record_id = data.get("record_id")
        method = data.get("generation_method", "context_aware")

        # If record_id is supplied, we can hydrate telemetry and prediction from existing record
        if record_id:
            record = BatteryData.query.get(record_id)
            if not record:
                return jsonify({"error": f"Battery record {record_id} not found"}), 404
            telemetry = {
                "voltage": record.voltage,
                "current": record.current,
                "soc": record.soc,
                "temp": record.temp,
                "degradation_level": record.degradation_level or 0.0
            }
            prediction = {
                "health_score": record.health_score,
                "status": record.status,
                "model_active": False
            }
            task = MaintenanceTask.query.filter_by(battery_record_id=record.id).order_by(MaintenanceTask.created_at.desc()).first()
            maintenance_plan = task.to_dict() if task else None

            report = create_and_persist_report(
                telemetry=telemetry,
                prediction=prediction,
                maintenance_plan=maintenance_plan,
                battery_record_id=record.id,
                generation_method=method
            )
            return jsonify(report), 200

        if not telemetry:
            return jsonify({"error": "Missing 'telemetry' or 'record_id' payload"}), 400

        prediction = data.get("prediction") or {
            "health_score": 85.0,
            "status": "Safe",
            "model_active": False
        }
        maintenance_plan = data.get("maintenance_plan")

        report = generate_diagnostic_report(
            telemetry=telemetry,
            prediction=prediction,
            maintenance_plan=maintenance_plan,
            generation_method=method
        )
        return jsonify(report), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/reports", methods=["GET"])
def list_reports():
    try:
        limit = request.args.get("limit", 20, type=int)
        reports = get_recent_reports(limit=limit)
        return jsonify(reports), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/reports/<int:report_id>", methods=["GET"])
def get_report(report_id):
    try:
        report = get_report_by_id(report_id)
        if not report:
            return jsonify({"error": "Diagnostic report not found"}), 404
        return jsonify(report), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/records/<int:record_id>/report", methods=["GET"])
def get_record_report(record_id):
    try:
        report = get_report_by_record_id(record_id)
        if not report:
            return jsonify({"error": f"No diagnostic report associated with record {record_id}"}), 404
        return jsonify(report), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

# ==================== ERROR HANDLERS ====================
@app.errorhandler(404)
def not_found(error):
    return send_from_directory('../frontend', 'index.html')

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000, threaded=True)
