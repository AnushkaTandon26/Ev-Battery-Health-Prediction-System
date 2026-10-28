from pathlib import Path
import warnings

import joblib
import numpy as np

MODEL_DIR = Path(__file__).resolve().parent / "model"
SCALER_PATH = MODEL_DIR / "ev_seq_scaler.pkl"
MODEL_PATH = sorted(MODEL_DIR.glob("*.keras"))[0] if list(MODEL_DIR.glob("*.keras")) else None
SEQUENCE_LENGTH = 128

_sequence_model = None
_sequence_scaler = None
_model_checked = False
_model_error = None


def _load_sequence_assets():
    global _sequence_model, _sequence_scaler, _model_checked, _model_error

    if _model_checked:
        return _sequence_model, _sequence_scaler

    _model_checked = True

    if not MODEL_PATH or not SCALER_PATH.exists():
        _model_error = "Model or scaler file missing."
        return None, None

    try:
        from tensorflow.keras.models import load_model
    except Exception as exc:
        _model_error = f"TensorFlow unavailable: {exc}"
        warnings.warn(_model_error)
        return None, None

    try:
        _sequence_scaler = joblib.load(SCALER_PATH)
        _sequence_model = load_model(MODEL_PATH)
    except Exception as exc:
        _model_error = f"Failed to load sequence model assets: {exc}"
        warnings.warn(_model_error)
        _sequence_model = None
        _sequence_scaler = None

    return _sequence_model, _sequence_scaler


def _record_to_features(record):
    voltage = float(record.get("voltage", 0.0))
    current = float(record.get("current", 0.0))
    soc = float(record.get("soc", 0.0))
    temp = float(record.get("temp", record.get("temperature", 0.0)))
    power = voltage * current
    return [voltage, current, soc, temp, power]


def _build_sequence(voltage, current, soc, temp, recent_records):
    records = recent_records or []
    sequence = [_record_to_features(record) for record in records[-(SEQUENCE_LENGTH - 1):]]
    sequence.append(_record_to_features({
        "voltage": voltage,
        "current": current,
        "soc": soc,
        "temp": temp
    }))

    if not sequence:
        sequence = [[voltage, current, soc, temp, voltage * current]]

    if len(sequence) > SEQUENCE_LENGTH:
        sequence = sequence[-SEQUENCE_LENGTH:]

    while len(sequence) < SEQUENCE_LENGTH:
        sequence.insert(0, sequence[0])

    return np.array(sequence, dtype=np.float32)


def _predict_with_sequence_model(voltage, current, soc, temp, recent_records):
    model, scaler = _load_sequence_assets()
    if model is None or scaler is None:
        return None

    sequence = _build_sequence(voltage, current, soc, temp, recent_records)
    scaled_sequence = scaler.transform(sequence)
    prediction = model.predict(scaled_sequence.reshape(1, SEQUENCE_LENGTH, 5), verbose=0)

    health_score = float(np.squeeze(prediction))
    if health_score <= 1.0:
        health_score *= 100.0

    return max(0.0, min(100.0, health_score))


def _predict_with_fallback(voltage, current, soc, temp):
    return max(0, min(100, 85 - abs(current) * 0.5 - abs(temp - 25) * 0.8 + soc * 0.3))


def _apply_degradation_adjustment(health_score, degradation_level):
    if degradation_level is None:
        return health_score

    degradation_level = max(0.0, min(100.0, float(degradation_level)))
    degradation_health = max(0.0, 100.0 - degradation_level)
    return max(0.0, min(100.0, (health_score * 0.72) + (degradation_health * 0.28)))


def _build_recommendations(temp, current, soc, health_score, degradation_level):
    recommendations = []
    if temp > 40:
        recommendations.append("Cool down battery immediately")
    if abs(current) > 50:
        recommendations.append("Reduce charging/discharging rate")
    if soc < 20:
        recommendations.append("Charge battery now")
    if degradation_level is not None and degradation_level >= 20:
        recommendations.append("Inspect degraded cells and verify pack balancing")
    if degradation_level is not None and degradation_level >= 35:
        recommendations.append("Plan battery module servicing or replacement review")
    if health_score < 50:
        recommendations.append("Schedule maintenance")
    return recommendations


def predict_battery_health(voltage, current, soc, temp, degradation_level=None, recent_records=None):
    """
    Predict battery health using the sequence model when available.

    The .keras model expects a 128 x 5 sequence. This backend builds that
    sequence from recent battery records plus the current input. The fifth
    feature is derived pack power (voltage * current).
    """
    health_score = _predict_with_sequence_model(voltage, current, soc, temp, recent_records)

    if health_score is None:
        health_score = _predict_with_fallback(voltage, current, soc, temp)

    health_score = _apply_degradation_adjustment(health_score, degradation_level)

    if health_score < 40:
        status = "Critical"
    elif health_score < 70:
        status = "Warning"
    else:
        status = "Safe"

    recommendations = _build_recommendations(temp, current, soc, health_score, degradation_level)

    return {
        "health_score": round(float(health_score), 2),
        "status": status,
        "recommendations": recommendations,
        "degradation_level": None if degradation_level is None else round(float(degradation_level), 2),
        "model_active": _sequence_model is not None,
        "model_error": _model_error
    }
