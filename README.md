# EV Battery Health Prediction System

An end-to-end Machine Learning and Natural Language Generation (NLG) system for Electric Vehicle (EV) battery State of Health (SOH) diagnostics, predictive degradation modeling, and automated expert maintenance planning.

## Quick Start (How to Run)

### 1. Run Backend Server
To start the backend with the Python virtual environment:
```powershell
.\.venv\Scripts\python.exe backend\app.py
```
Alternatively, using the top-level runner:
```bash
python run.py --backend
```
The Flask backend runs at `http://127.0.0.1:5000`.

### 2. Open the Dashboard
Open `http://127.0.0.1:5000` in your web browser. The responsive dashboard allows you to:
- Input real-time battery parameters (Voltage, Current, SOC, Temperature, Degradation rate)
- Receive instant SOH predictions and health classification
- Generate a comprehensive, facts-first NLG diagnostic report
- View historical telemetry charts and aggregate statistics

### 3. Run Test Suite
To run all 39 unit and integration tests:
```powershell
.\.venv\Scripts\python.exe -m unittest discover tests
```

### 4. Run Model Training (Optional)
```powershell
python run.py --train
```

---

## Features
- **Real-Time SOH Prediction**: Deep learning model trained on battery cycling data.
- **Facts-First NLG Diagnostic Engine**: Deterministic rule-based fact extraction, discourse planning, template realization, and strict schema validation for zero hallucination risk.
- **Interactive UI Dashboard**: Modern responsive UI with live gauge cards, trend charts, and diagnostic modal.
- **SQLite Database Persistence**: Secure local storage of telemetry records, historical predictions, and diagnostic reports.
- **Serverless Vercel Deployment**: Configured via `vercel.json` and WSGI bridge in `api/index.py`.
- **Automated Architecture & PPT Diagram Generation**: Python scripts (`generate_architecture.py`, `generate_ppt_images.py`) for producing publication-quality diagrams.

---

## Project Structure
```text
.
|-- api/
|   `-- index.py                      # Vercel serverless entrypoint
|-- backend/
|   |-- app.py                        # Flask API application and routes
|   |-- agentic_ai.py                 # Agentic recommendation logic
|   |-- database.py                   # SQLAlchemy models (BatteryData, DiagnosticReport)
|   |-- report_service.py             # Diagnostic report orchestration service
|   |-- utils.py                      # Preprocessing, scaling, and model inference
|   |-- model/
|   |   |-- ev_model_best (1).keras   # Trained Keras neural network model
|   |   `-- ev_seq_scaler.pkl         # Fitted feature standardizer
|   `-- nlg/                          # Natural Language Generation pipeline
|       |-- config.py                 # NLG threshold constants and rules
|       |-- diagnostic_rules.py       # Rule engine for finding generation
|       |-- fact_extractor.py         # Telemetry feature extraction
|       |-- report_planner.py         # Discourse structure planner
|       |-- report_validator.py       # Fact consistency and schema validator
|       |-- schema.py                 # Domain dataclasses
|       `-- sentence_realizer.py      # Text generation templates
|-- evaluation/
|   |-- corpus.py                     # Synthetic evaluation test cases
|   |-- evaluate.py                   # NLG benchmark evaluation runner
|   `-- evaluation_results.json       # Benchmark evaluation metrics
|-- frontend/
|   |-- index.html                    # Main dashboard HTML
|   |-- script.js                     # Dashboard interaction, charts, and API calls
|   `-- styles.css                    # Responsive CSS styling
|-- ppt_images/                       # Architecture diagrams and presentation graphics
|-- tests/
|   |-- test_api_endpoints.py         # Flask REST API endpoint tests
|   `-- test_nlg_units.py             # NLG pipeline unit test suite (39 tests)
|-- generate_architecture.py          # System architecture generator
|-- generate_ppt_images.py            # Presentation slide visual generator
|-- requirements.txt                  # Python dependencies
|-- run.py                            # CLI entrypoint (--backend, --train, --eval)
|-- vercel.json                       # Vercel deployment configuration
`-- README.md                         # Documentation
```
