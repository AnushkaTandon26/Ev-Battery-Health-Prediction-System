from flask import Flask, jsonify, request
from flask_cors import CORS
from backend.database import db, BatteryData
from backend.utils import predict_soh, get_health_status
from backend.agentic_ai import generate_maintenance_plan

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ev_battery.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)
db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/api/predict', methods=['POST'])
def predict():
    data = request.get_json() or {}
    v = float(data.get('voltage', 3.7))
    i = float(data.get('current', 1.0))
    soc = float(data.get('soc', 80.0))
    temp = float(data.get('temp', 25.0))
    deg = float(data.get('degradation', 0.05))
    soh = predict_soh(v, i, soc, temp, deg)
    status = get_health_status(soh)
    rec = BatteryData(voltage=v, current=i, soc=soc, temp=temp, degradation=deg, soh_prediction=soh)
    db.session.add(rec)
    db.session.commit()
    maint = generate_maintenance_plan(soh, temp, deg)
    return jsonify({'soh_prediction': soh, 'health_status': status, 'maintenance_recommendations': maint, 'record_id': rec.id})

@app.route('/api/history', methods=['GET'])
def get_history():
    limit = int(request.args.get('limit', 20))
    records = BatteryData.query.order_by(BatteryData.id.desc()).limit(limit).all()
    return jsonify([r.to_dict() for r in records])
