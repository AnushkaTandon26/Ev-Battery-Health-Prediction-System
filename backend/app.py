from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json

from agentic_ai import build_maintenance_plan
from database import db, BatteryData, MaintenanceTask, ensure_schema
from utils import predict_battery_health

app = Flask(__name__, static_folder='../frontend', static_url_path='')
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
            "POST /api/predict": "Make prediction & save",
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
        data = request.json
        
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
            "model_error": prediction.get("model_error")
        }), 200
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
