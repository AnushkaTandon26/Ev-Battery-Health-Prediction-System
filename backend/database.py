from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
from sqlalchemy import inspect, text

db = SQLAlchemy()

class BatteryData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    voltage = db.Column(db.Float, nullable=False)
    current = db.Column(db.Float, nullable=False)
    soc = db.Column(db.Float, nullable=False)
    temp = db.Column(db.Float, nullable=False)
    degradation_level = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), nullable=False)
    health_score = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'voltage': self.voltage,
            'current': self.current,
            'soc': self.soc,
            'temp': self.temp,
            'degradation_level': self.degradation_level,
            'status': self.status,
            'health_score': self.health_score,
            'timestamp': self.timestamp.isoformat()
        }


class MaintenanceTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    battery_record_id = db.Column(db.Integer, nullable=False, index=True)
    task_type = db.Column(db.String(50), nullable=False)
    priority = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    action_status = db.Column(db.String(30), nullable=False, default="Scheduled")
    execution_mode = db.Column(db.String(30), nullable=False, default="Autonomous")
    assigned_team = db.Column(db.String(50), nullable=False, default="EV Service Desk")
    scheduled_for = db.Column(db.DateTime, nullable=False)
    recommended_actions = db.Column(db.Text, nullable=False, default="[]")
    automation_notes = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        try:
            actions = json.loads(self.recommended_actions or "[]")
        except json.JSONDecodeError:
            actions = []

        return {
            'id': self.id,
            'battery_record_id': self.battery_record_id,
            'task_type': self.task_type,
            'priority': self.priority,
            'title': self.title,
            'summary': self.summary,
            'action_status': self.action_status,
            'execution_mode': self.execution_mode,
            'assigned_team': self.assigned_team,
            'scheduled_for': self.scheduled_for.isoformat() if self.scheduled_for else None,
            'recommended_actions': actions,
            'automation_notes': self.automation_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }


def ensure_schema():
    inspector = inspect(db.engine)

    if "battery_data" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("battery_data")}
    if "degradation_level" not in columns:
        with db.engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE battery_data ADD COLUMN degradation_level FLOAT DEFAULT 0")
            )
