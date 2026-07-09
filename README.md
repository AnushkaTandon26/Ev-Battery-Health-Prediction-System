# EV Battery Health Prediction System

Predictive health monitoring and State of Health (SOH) tracking for EV lithium-ion battery packs.

## Battery Telemetry Inputs
- Voltage (V): 2.5V - 4.35V nominal cell range
- Current (A): Dynamic charge/discharge current
- State of Charge (SOC %): 0 - 100%
- Temperature (C): Operating cell temperature
- Degradation Rate (%/1k cycles)

## Quick Start
```bash
pip install -r requirements.txt
python run.py --backend
```

## Database
Stores battery telemetry in SQLite with `BatteryData` table.

## SOH Model
Trained deep learning model stored in `backend/model/` with fallback support.
- Input features: Voltage, Current, SOC, Temperature, Degradation rate
