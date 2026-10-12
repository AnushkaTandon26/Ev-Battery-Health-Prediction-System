# EV Battery Health Prediction System — with NLP/NLG Diagnostic Reports

An EV battery health prediction dashboard (Flask + SQLite + vanilla JS)
extended with a **Natural Language Generation (NLG)** layer that turns the
numeric prediction into a clear, evidence-grounded, plain-English diagnostic
report.

The NLG layer is the academic NLP contribution: a deterministic, auditable
**facts-first pipeline** — validation → fact extraction → rule engine →
content planning → sentence realization → report validation — not a few
hard-coded sentences and not a free-form chatbot.

## Features

- Battery health prediction (Keras sequence model with a heuristic fallback)
- Agentic maintenance plan generation
- SQLite-backed history and statistics
- **NEW:** NLG diagnostic report generated from the real prediction output
- **NEW:** report persistence (`DiagnosticReport`) and retrieval API
- **NEW:** dashboard report panel with findings, evidence, actions, limitations
- **NEW:** reproducible NLP evaluation over a fixed synthetic corpus
- **NEW:** unit + API/integration tests

## Quick Start

```bash
# 1. install dependencies (see note on TensorFlow below)
pip install -r requirements.txt

# 2. run the backend
python run.py --backend
# or:  python backend/app.py

# 3. open the dashboard
#    http://127.0.0.1:5000
```

Data is stored in `instance/ev_battery.db` (created automatically; existing
databases are migrated non-destructively).

### Configuration (environment variables)

| Variable | Purpose | Default |
|---|---|---|
| `EV_SECRET_KEY` | Flask secret key | dev placeholder |
| `EV_DEBUG` | `1` enables Flask debug (local only) | `0` (off) |

## NLP/NLG architecture

```
request → validation → prediction (existing) → maintenance plan (existing)
        → fact extraction → rule engine → content planning
        → sentence realization → report validation → persist → API → dashboard
```

Modules (`backend/nlg/`):

| File | Responsibility |
|---|---|
| `config.py` | Versioned thresholds, units, labels, disclaimers (single source of truth) |
| `validation.py` | Input validation (types, finite, ranges) — never invents data |
| `fact_extractor.py` | Canonical, source-tagged `DiagnosticFacts` object |
| `diagnostic_rules.py` | Deterministic rule engine → `Finding` objects with evidence |
| `report_planner.py` | Content selection, ordering, de-duplicated recommendations |
| `sentence_realizer.py` | Context-aware generator **and** a baseline template generator |
| `report_generator.py` | Orchestration → schema-shaped report object |
| `report_validator.py` | Grounding + safety checks (no fabricated numbers / unsafe claims) |
| `schema.py` | Validates report JSON against `diagnostic_report.schema.json` |

Why two generators? `sentence_realizer.realize(plan, method="baseline")` is a
naive fixed-template generator; `method="context_aware"` (default) adds
aggregation, severity-aware ordering, referring expressions and redundancy
reduction. The evaluation script compares the two.

## Model behaviour (read this — it is a real discrepancy)

- Runtime inference (`backend/utils.py`) loads a **Keras** 128×5 sequence model
  (`backend/model/ev_model_best (1).keras`) plus a MinMax **sequence scaler**
  (`ev_seq_scaler.pkl`). Features: voltage, current, SOC, temperature, derived
  power. Degradation is applied as a *post-hoc adjustment*, not a model input.
- The separate training script (`model/train.py`) trains a **scikit-learn
  RandomForestRegressor** on synthetic data and saves `ev_battery_model.pkl` —
  a **different artifact that the runtime never loads**. Running
  `python run.py --train` does **not** update the deployed Keras model.
- If TensorFlow or the model assets are unavailable, the predictor falls back
  to a documented heuristic. This is disclosed through `model_active` /
  `model_error` in the API and in every report's `model_status` + limitations.
- The health score is **not** a scientifically validated real-world SOH figure,
  especially under the fallback path. The report wording reflects this.

## API

Existing endpoints are preserved. `POST /api/predict` gains **additive** fields
only (`report_status`, `report_error_code`, `diagnostic_report`); report
failure never discards a saved prediction.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/predict` | Predict + save + generate report (additive fields) |
| GET | `/api/history?limit=` | Recent battery records |
| GET | `/api/stats` | Summary stats |
| GET | `/api/detailed-stats` | Averages + records |
| GET | `/api/agent/tasks?limit=` | Maintenance tasks |
| POST | `/api/reports/generate` | Report for a saved `record_id` (no re-predict) |
| GET | `/api/reports?limit=` | Report summaries, newest first |
| GET | `/api/reports/<report_id>` | One full report |
| GET | `/api/records/<record_id>/report` | Latest report for a record |

Error envelope: `{"error": {"code", "message", "details"}}` with
`400` (bad request), `404` (not found), `422` (invalid/insufficient data),
`500` (internal). Stack traces are never returned to the client.

Example `POST /api/predict` response (abbreviated):

```json
{
  "health_score": 74.0, "status": "Safe", "record_id": 17,
  "model_active": true, "model_error": null,
  "report_status": "generated",
  "diagnostic_report": {
    "schema_version": "1.0", "report_id": 5, "battery_record_id": 17,
    "overall_status": "Safe", "generation_method": "template_nlg",
    "model_status": "keras", "summary": "The predicted battery health is 74 %...",
    "measurements": [...], "findings": [...],
    "recommendations": [...], "limitations": [...], "source_snapshot": {...}
  }
}
```

The report JSON conforms to `project-docs/diagnostic_report.schema.json`
(a bundled copy lives at `backend/nlg/diagnostic_report.schema.json`).

## Testing

```bash
# all tests (API tests auto-skip if Flask is not installed)
python -m unittest discover -s tests -v
```

- `tests/test_nlg_pipeline.py` — validation, rule boundaries, trend/conflict,
  report generation, grounding/safety, schema (29 tests, no Flask needed).
- `tests/test_api.py` — `/api/predict` + report endpoints against an in-memory
  SQLite DB (10 tests, requires Flask/Flask-SQLAlchemy).

## NLP evaluation

```bash
python evaluation/evaluate.py            # prints a metrics table
python evaluation/evaluate.py --json out.json
```

Runs the pipeline over `evaluation/corpus.json` (10 **synthetic** scenarios:
safe, low SOC, elevated temp, high current, high degradation, multi-critical,
model fallback, boundary temp, declining trend, safe-vs-critical conflict) and
compares the context-aware generator against the baseline. Metrics: generation
success, grounding pass rate, unsupported-claim rate, finding coverage,
recommendation coverage, Flesch reading ease, redundancy, ROUGE-1 vs reference,
word count, latency.

> ROUGE-1 measures lexical overlap with a reference text, **not** diagnostic
> correctness. The corpus is synthetic and the reference reports are
> illustrative, not manufacturer-approved diagnostics.

## File structure

```text
backend/
  app.py                 # routes (+ report endpoints, validation, error envelope)
  agentic_ai.py          # maintenance planner (unchanged)
  database.py            # BatteryData, MaintenanceTask, DiagnosticReport (new)
  utils.py               # predictor (Keras + fallback) (unchanged)
  report_service.py      # generate + persist helper (new)
  nlg/                   # NLG pipeline (new)
  model/                 # Keras model + scaler
frontend/                # dashboard (report panel added)
tests/                   # unit + API tests (new)
evaluation/              # corpus.json + evaluate.py (new)
```

## Limitations

- Thresholds are **project defaults**, not certified manufacturer limits.
- `degradation_level` semantics are undefined by the system; it is treated as a
  neutral index, never asserted as capacity loss.
- Reports are decision-support only; they never certify a vehicle as safe to
  drive/charge, nor claim a confirmed fault.
- The sandbox used to build this could not install Flask/TensorFlow; see the
  completion notes for exactly which suites were run vs. not run.
```
