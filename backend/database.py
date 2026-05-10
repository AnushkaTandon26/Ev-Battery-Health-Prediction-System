from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class BatteryData(db.Model):
    __tablename__ = 'battery_data'
    id = db.Column(db.Integer, primary_key=True)
    voltage = db.Column(db.Float, nullable=False)
    current = db.Column(db.Float, nullable=False)
    soc = db.Column(db.Float, nullable=False)
    temp = db.Column(db.Float, nullable=False)
    degradation = db.Column(db.Float, nullable=False)
    soh_prediction = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'voltage': self.voltage,
            'current': self.current,
            'soc': self.soc,
            'temp': self.temp,
            'degradation': self.degradation,
            'soh_prediction': self.soh_prediction,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
