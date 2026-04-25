# EV Battery Health Prediction System

## Features
- Real-time battery health prediction
- SQLite-backed history and statistics
- Responsive live dashboard served by Flask
- Agentic maintenance plan generation
- Optional model training workflow

## Quick Start

1. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

2. Start the backend
   ```bash
   python run.py --backend
   ```
   The app runs at `http://127.0.0.1:5000`

3. Open the dashboard
   - Open `http://127.0.0.1:5000`
   - The active dashboard is `frontend/index.html`

4. Train the model if needed
   ```bash
   python run.py --train
   ```

## Usage
- Enter Voltage, Current, SOC, Temperature, and Degradation
- Run a prediction
- Review history, stats, and maintenance recommendations
- Data is stored in `instance/ev_battery.db`

## Active File Structure
```text
.
|-- backend/
|   |-- app.py
|   |-- agentic_ai.py
|   |-- database.py
|   |-- utils.py
|   `-- model/
|       |-- ev_model_best (1).keras
|       `-- ev_seq_scaler.pkl
|-- frontend/
|   |-- index.html
|   |-- script.js
|   `-- styles.css
|-- instance/
|   `-- ev_battery.db
|-- model/
|   |-- requirements.txt
|   `-- train.py
|-- requirements.txt
|-- run.py
`-- README.md
```
