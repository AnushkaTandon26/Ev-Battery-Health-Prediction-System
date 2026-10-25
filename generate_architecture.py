"""
Generate a presentation-grade system architecture diagram
styled with a light pastel gradient background, colored groups,
nested sub-components, and directional flow arrows — matching
the academic poster / detailed flowchart reference style.
"""
import subprocess, tempfile, shutil
from pathlib import Path
from PIL import Image, ImageChops

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUT_DIR = Path("d:/ev battery health prediction system/ppt_images")
OUT_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR = Path(r"C:\Users\User\.gemini\antigravity\brain\e0a4c102-950e-44bf-b048-732a071e0012")

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: linear-gradient(135deg, #eef2ff 0%, #fdf2f8 25%, #f0f9ff 50%, #faf5ff 75%, #ecfdf5 100%);
  font-family: 'Inter', 'Segoe UI', sans-serif;
  color: #1e293b;
  padding: 32px;
  display: flex;
  justify-content: center;
}

.root { width: 1200px; }

/* ── Title Block ──────────────────────── */
.title-block {
  text-align: center;
  margin-bottom: 8px;
}
.title-block h1 {
  font-size: 1.45rem;
  font-weight: 900;
  color: #0f172a;
  letter-spacing: -0.3px;
  text-transform: uppercase;
}
.title-block .inst {
  display: inline-block;
  margin-top: 6px;
  border: 1.5px solid #cbd5e1;
  border-radius: 6px;
  padding: 4px 16px;
  font-size: 0.72rem;
  font-weight: 600;
  color: #475569;
  background: #ffffff;
}

/* ── Phase Headers ────────────────────── */
.phase-row {
  display: flex;
  gap: 12px;
  margin: 14px 0 10px;
  align-items: center;
  justify-content: center;
}
.phase-label {
  padding: 6px 18px;
  border-radius: 8px;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  color: #ffffff;
}
.phase-label--left  { background: linear-gradient(135deg, #6366f1, #8b5cf6); }
.phase-label--right { background: linear-gradient(135deg, #0ea5e9, #06b6d4); }
.phase-connector {
  flex: 1;
  height: 0;
  border-top: 2px dashed #94a3b8;
  position: relative;
}
.phase-connector-text {
  position: absolute;
  top: -10px;
  left: 50%;
  transform: translateX(-50%);
  background: #f1f5f9;
  padding: 0 8px;
  font-size: 0.6rem;
  color: #64748b;
  font-weight: 600;
  white-space: nowrap;
}

/* ── Main Layout ──────────────────────── */
.main-layout {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}
.col-left  { flex: 1; }
.col-right { flex: 1; }

/* ── Group Boxes ──────────────────────── */
.group {
  border-radius: 14px;
  padding: 14px;
  margin-bottom: 12px;
  position: relative;
  background: rgba(255,255,255,0.55);
  backdrop-filter: blur(4px);
}
.group-label {
  position: absolute;
  top: -9px; left: 16px;
  padding: 2px 10px;
  border-radius: 5px;
  font-size: 0.6rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: #fff;
}

/* Group themes */
.group--indigo { border: 2px solid #818cf8; }
.group--indigo .group-label { background: #6366f1; }

.group--violet { border: 2px solid #a78bfa; }
.group--violet .group-label { background: #8b5cf6; }

.group--amber { border: 2px solid #fbbf24; }
.group--amber .group-label { background: #f59e0b; }

.group--sky { border: 2px solid #38bdf8; }
.group--sky .group-label { background: #0ea5e9; }

.group--emerald { border: 2px solid #34d399; }
.group--emerald .group-label { background: #10b981; }

.group--rose { border: 2px solid #fb7185; }
.group--rose .group-label { background: #f43f5e; }

.group--teal { border: 2px solid #2dd4bf; }
.group--teal .group-label { background: #14b8a6; }

.group--purple { border: 2px solid #c084fc; }
.group--purple .group-label { background: #a855f7; }

.group--blue { border: 2px solid #60a5fa; }
.group--blue .group-label { background: #3b82f6; }

.group--orange { border: 2px solid #fb923c; }
.group--orange .group-label { background: #f97316; }

/* ── Component Boxes ──────────────────── */
.comp {
  border-radius: 8px;
  padding: 8px 10px;
  margin-bottom: 6px;
  font-size: 0.68rem;
  line-height: 1.4;
  border: 1.5px solid;
}
.comp-name {
  font-weight: 800;
  font-size: 0.72rem;
  margin-bottom: 2px;
  display: flex;
  align-items: center;
  gap: 5px;
}
.comp-desc {
  color: #475569;
  font-size: 0.62rem;
}
.comp-tags {
  display: flex;
  gap: 4px;
  margin-top: 4px;
  flex-wrap: wrap;
}
.tag {
  font-size: 0.54rem;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 3px;
  background: rgba(0,0,0,0.06);
  color: #64748b;
  border: 1px solid rgba(0,0,0,0.08);
}

/* Comp colour variants */
.comp--indigo  { background: #eef2ff; border-color: #c7d2fe; }
.comp--violet  { background: #f5f3ff; border-color: #ddd6fe; }
.comp--amber   { background: #fffbeb; border-color: #fde68a; }
.comp--sky     { background: #f0f9ff; border-color: #bae6fd; }
.comp--emerald { background: #ecfdf5; border-color: #a7f3d0; }
.comp--rose    { background: #fff1f2; border-color: #fecdd3; }
.comp--teal    { background: #f0fdfa; border-color: #99f6e4; }
.comp--purple  { background: #faf5ff; border-color: #e9d5ff; }
.comp--blue    { background: #eff6ff; border-color: #bfdbfe; }
.comp--orange  { background: #fff7ed; border-color: #fed7aa; }
.comp--white   { background: #ffffff; border-color: #e2e8f0; }

/* ── Arrows ───────────────────────────── */
.arrow-down {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 28px;
  position: relative;
}
.arrow-down .shaft {
  width: 2.5px;
  height: 16px;
  background: #94a3b8;
}
.arrow-down .head {
  width: 0; height: 0;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-top: 7px solid #94a3b8;
  position: absolute;
  bottom: 2px;
}
.arrow-down .a-label {
  position: absolute;
  right: 30%;
  font-size: 0.56rem;
  color: #64748b;
  font-weight: 600;
  font-style: italic;
}
.arrow-right-inline {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 4px 0;
}
.arrow-right-inline .shaft-h {
  width: 30px;
  height: 2px;
  background: #94a3b8;
}
.arrow-right-inline .head-r {
  width: 0; height: 0;
  border-top: 5px solid transparent;
  border-bottom: 5px solid transparent;
  border-left: 6px solid #94a3b8;
}
.arrow-right-inline .a-label-h {
  font-size: 0.54rem;
  color: #64748b;
  font-weight: 600;
  margin: 0 4px;
  white-space: nowrap;
}

/* ── Horizontal flow strip ────────────── */
.flow-strip {
  display: flex;
  align-items: center;
  gap: 0;
  padding: 8px 10px;
  background: rgba(245,158,11,0.08);
  border: 1.5px solid #fde68a;
  border-radius: 8px;
  margin-top: 6px;
  justify-content: center;
}
.fs-step {
  display: flex;
  align-items: center;
  gap: 4px;
}
.fs-num {
  width: 22px; height: 22px;
  border-radius: 50%;
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: #fff;
  font-size: 0.62rem;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.fs-text {
  font-size: 0.58rem;
  font-weight: 700;
  color: #92400e;
  white-space: nowrap;
}
.fs-arrow {
  width: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #d97706;
  font-size: 0.8rem;
  font-weight: 700;
}

/* ── Rows ─────────────────────────────── */
.row-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.row-3 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
}
.row-4 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 1fr;
  gap: 8px;
}

/* ── Side output box ──────────────────── */
.output-card {
  background: #ffffff;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px;
  text-align: center;
}
.output-card .icon-big {
  font-size: 2rem;
  margin-bottom: 6px;
}
.output-card h4 {
  font-size: 0.78rem;
  font-weight: 800;
  color: #0f172a;
}
.output-card p {
  font-size: 0.6rem;
  color: #64748b;
  margin-top: 3px;
}

/* ── Bottom bar ───────────────────────── */
.bottom-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding: 6px 16px;
  background: rgba(255,255,255,0.7);
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}
.bottom-bar .dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: #22c55e;
  display: inline-block;
  margin-right: 6px;
  box-shadow: 0 0 6px #22c55e;
}
.bottom-bar span {
  font-size: 0.62rem;
  font-weight: 600;
  color: #64748b;
}

/* ── Legend ────────────────────────────── */
.legend {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-top: 8px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.58rem;
  color: #64748b;
  font-weight: 600;
}
.legend-line {
  width: 22px; height: 2.5px;
  border-radius: 2px;
}
.legend-line--solid { background: #94a3b8; }
.legend-line--dashed { background: repeating-linear-gradient(90deg, #94a3b8, #94a3b8 4px, transparent 4px, transparent 8px); }
.legend-line--data  { background: #6366f1; }

/* ── Full-width sections ──────────────── */
.full-section {
  margin-top: 4px;
}
</style>
</head>
<body>
<div class="root">

  <!-- ═══════ TITLE ═══════ -->
  <div class="title-block">
    <h1>EV Battery Health Prediction & NLG Diagnostic Reporting System</h1>
    <div class="inst">AI in EV Battery Diagnostics and Performance Optimisation | NLP Project | BIONS</div>
  </div>

  <!-- ═══════ PHASE HEADERS ═══════ -->
  <div class="phase-row">
    <div class="phase-label phase-label--left">Phase 1: Offline Training & Model Pipeline</div>
    <div class="phase-connector">
      <span class="phase-connector-text">Trained Model Weights & Rule Config</span>
    </div>
    <div class="phase-label phase-label--right">Phase 2: Online Inference & Reporting System</div>
  </div>

  <!-- ═══════ MAIN TWO-COLUMN LAYOUT ═══════ -->
  <div class="main-layout">

    <!-- ▬▬▬ LEFT COLUMN: Offline / Backend Pipeline ▬▬▬ -->
    <div class="col-left">

      <!-- Input / Telemetry Ingestion -->
      <div class="group group--indigo">
        <span class="group-label">Data Ingestion & Pre-Processing</span>
        <div style="margin-top:4px;">
          <div class="comp comp--indigo">
            <div class="comp-name">&#x1F50C; Telemetry Input Stream</div>
            <div class="comp-desc">Multivariate sensor data: pack voltage (V), current (A), SOC (%), temperature (&deg;C), degradation index</div>
            <div class="comp-tags"><span class="tag">BMS CAN Bus</span><span class="tag">REST /api/predict</span></div>
          </div>
          <div class="row-2">
            <div class="comp comp--sky">
              <div class="comp-name">&#x1F4CA; Sensor Normaliser</div>
              <div class="comp-desc">Unit conversion, range validation, derived metric computation (pack power in W)</div>
              <div class="comp-tags"><span class="tag">NumPy</span><span class="tag">Pandas</span></div>
            </div>
            <div class="comp comp--emerald">
              <div class="comp-name">&#x2705; Input Validation</div>
              <div class="comp-desc">Schema enforcement, missing-value handling, safety bounds check</div>
              <div class="comp-tags"><span class="tag">Flask Request</span><span class="tag">JSON Schema</span></div>
            </div>
          </div>
        </div>
      </div>

      <div class="arrow-down"><div class="shaft"></div><div class="head"></div><span class="a-label">validated telemetry vectors</span></div>

      <!-- ML Prediction -->
      <div class="group group--violet">
        <span class="group-label">Prediction & Intelligence Engine</span>
        <div style="margin-top:4px;">
          <div class="comp comp--violet">
            <div class="comp-name">&#x1F9E0; ML Prediction Engine</div>
            <div class="comp-desc">Hybrid LSTM-RNN sequence model for SOH and RUL estimation with heuristic fallback</div>
            <div class="comp-tags"><span class="tag">TensorFlow / Keras</span><span class="tag">scikit-learn</span></div>
          </div>
          <div class="row-2">
            <div class="comp comp--rose">
              <div class="comp-name">&#x26A0;&#xFE0F; Anomaly Detector</div>
              <div class="comp-desc">Configurable threshold rules for temperature, voltage band, and degradation</div>
              <div class="comp-tags"><span class="tag">Prototype Rules</span><span class="tag">Confidence Scores</span></div>
            </div>
            <div class="comp comp--purple">
              <div class="comp-name">&#x1F916; Agentic AI Planner</div>
              <div class="comp-desc">Autonomous maintenance task generation, severity scoring, team routing</div>
              <div class="comp-tags"><span class="tag">Rule Engine</span><span class="tag">Priority Queue</span></div>
            </div>
          </div>
        </div>
      </div>

      <div class="arrow-down"><div class="shaft"></div><div class="head"></div><span class="a-label">prediction + anomaly flags</span></div>

      <!-- NLG Pipeline (full width, detailed) -->
      <div class="group group--amber">
        <span class="group-label">Natural Language Generation (NLG) Pipeline</span>
        <div style="margin-top:4px;">
          <div class="row-4">
            <div class="comp comp--amber">
              <div class="comp-name">&#x1F4CA; Facts Extractor</div>
              <div class="comp-desc">Structured telemetry & prediction facts with provenance tracking</div>
              <div class="comp-tags"><span class="tag">Zero Hallucination</span></div>
            </div>
            <div class="comp comp--orange">
              <div class="comp-name">&#x1F4DD; Document Planner</div>
              <div class="comp-desc">Content selection, severity ordering, rhetorical structuring</div>
              <div class="comp-tags"><span class="tag">RST Planning</span></div>
            </div>
            <div class="comp comp--amber">
              <div class="comp-name">&#x1F4AC; Sentence Realiser</div>
              <div class="comp-desc">Context-aware & baseline template engines</div>
              <div class="comp-tags"><span class="tag">Dual Mode</span></div>
            </div>
            <div class="comp comp--orange">
              <div class="comp-name">&#x1F6E1;&#xFE0F; Schema Validator</div>
              <div class="comp-desc">JSON schema verification, grounding fidelity</div>
              <div class="comp-tags"><span class="tag">39-Test Suite</span></div>
            </div>
          </div>
          <div class="flow-strip">
            <div class="fs-step"><div class="fs-num">1</div><span class="fs-text">Extract Facts</span></div>
            <div class="fs-arrow">&#x2192;</div>
            <div class="fs-step"><div class="fs-num">2</div><span class="fs-text">Plan Document</span></div>
            <div class="fs-arrow">&#x2192;</div>
            <div class="fs-step"><div class="fs-num">3</div><span class="fs-text">Realise Sentences</span></div>
            <div class="fs-arrow">&#x2192;</div>
            <div class="fs-step"><div class="fs-num">4</div><span class="fs-text">Validate & Ground</span></div>
            <div class="fs-arrow">&#x2192;</div>
            <div class="fs-step"><div class="fs-num">5</div><span class="fs-text">Render Report</span></div>
          </div>
        </div>
      </div>

    </div>

    <!-- ▬▬▬ RIGHT COLUMN: Online / Serving ▬▬▬ -->
    <div class="col-right">

      <!-- API & Persistence -->
      <div class="group group--sky">
        <span class="group-label">REST API & Persistence Layer</span>
        <div style="margin-top:4px;">
          <div class="comp comp--sky">
            <div class="comp-name">&#x1F310; Flask REST API Server</div>
            <div class="comp-desc">RESTful endpoints: /predict, /reports/generate, /history, /stats, /agent/tasks, /reports/&lt;id&gt;</div>
            <div class="comp-tags"><span class="tag">Flask 3.0</span><span class="tag">Flask-CORS</span><span class="tag">Gunicorn</span></div>
          </div>
          <div class="row-2">
            <div class="comp comp--blue">
              <div class="comp-name">&#x1F5C4;&#xFE0F; SQLAlchemy ORM</div>
              <div class="comp-desc">Battery records, diagnostic reports, maintenance tasks with full audit trail</div>
              <div class="comp-tags"><span class="tag">SQLite</span><span class="tag">/tmp on Vercel</span></div>
            </div>
            <div class="comp comp--teal">
              <div class="comp-name">&#x1F4E6; Report Service</div>
              <div class="comp-desc">Persist & retrieve structured NLG diagnostic reports by record or report ID</div>
              <div class="comp-tags"><span class="tag">JSON Serialisation</span></div>
            </div>
          </div>
        </div>
      </div>

      <div class="arrow-down"><div class="shaft"></div><div class="head"></div><span class="a-label">JSON API responses</span></div>

      <!-- Cloud Deployment -->
      <div class="group group--emerald">
        <span class="group-label">Cloud Deployment & CI/CD</span>
        <div style="margin-top:4px;">
          <div class="comp comp--emerald">
            <div class="comp-name">&#x2601;&#xFE0F; Vercel Serverless Runtime</div>
            <div class="comp-desc">Python 3.12 WSGI with @vercel/python, auto-deploy on git push to main, global CDN edge network</div>
            <div class="comp-tags"><span class="tag">@vercel/python</span><span class="tag">vercel.json</span><span class="tag">api/index.py</span></div>
          </div>
          <div class="comp comp--white">
            <div class="comp-name">&#x1F4E1; GitHub CI/CD Pipeline</div>
            <div class="comp-desc">Push to main &#x2192; Auto build &#x2192; Vercel deploys &#x2192; Live at ev-battery-health-prediction-system.vercel.app</div>
            <div class="comp-tags"><span class="tag">Git Integration</span><span class="tag">Auto Deploy</span></div>
          </div>
        </div>
      </div>

      <div class="arrow-down"><div class="shaft"></div><div class="head"></div><span class="a-label">serves static + API</span></div>

      <!-- Frontend / UI -->
      <div class="group group--rose">
        <span class="group-label">Interactive Frontend Dashboard</span>
        <div style="margin-top:4px;">
          <div class="row-2">
            <div class="comp comp--rose">
              <div class="comp-name">&#x1F4F1; Multi-Tab SPA</div>
              <div class="comp-desc">Dashboard, Vehicle, Configuration, History, Report, Messages, Settings, Favourites</div>
              <div class="comp-tags"><span class="tag">Vanilla JS</span><span class="tag">CSS Grid</span></div>
            </div>
            <div class="comp comp--purple">
              <div class="comp-name">&#x1F4C4; NLG Report Panel</div>
              <div class="comp-desc">Context-Aware / Baseline mode selector, summary, findings, actions, limitations</div>
              <div class="comp-tags"><span class="tag">Dark UI</span><span class="tag">Responsive</span></div>
            </div>
          </div>
          <div class="comp comp--white">
            <div class="comp-name">&#x1F4C8; Health Analytics & Gauges</div>
            <div class="comp-desc">Real-time gauges (SOC, temperature, health), history table, favourite KPIs, recommendations feed</div>
            <div class="comp-tags"><span class="tag">Live Polling 30s</span><span class="tag">Geolocation</span><span class="tag">Charts</span></div>
          </div>
        </div>
      </div>

      <div class="arrow-down"><div class="shaft"></div><div class="head"></div><span class="a-label">renders to user</span></div>

      <!-- User Output -->
      <div class="group group--blue" style="padding: 10px 14px;">
        <span class="group-label">User-Facing Output</span>
        <div style="margin-top:4px; display: flex; gap: 8px;">
          <div class="output-card" style="flex:1;">
            <div class="icon-big">&#x1F4CB;</div>
            <h4>Diagnostic Report</h4>
            <p>Plain-English grounded summary with findings, severity, and limitations</p>
          </div>
          <div class="output-card" style="flex:1;">
            <div class="icon-big">&#x1F527;</div>
            <h4>Maintenance Plan</h4>
            <p>Autonomous agent tasks with priority, assigned team, and action status</p>
          </div>
          <div class="output-card" style="flex:1;">
            <div class="icon-big">&#x2764;&#xFE0F;</div>
            <h4>Health Score</h4>
            <p>Predicted SOH %, condition label, RUL estimation</p>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ═══════ LEGEND ═══════ -->
  <div class="legend">
    <div class="legend-item"><div class="legend-line legend-line--solid"></div> Data Flow</div>
    <div class="legend-item"><div class="legend-line legend-line--dashed"></div> Config / Weights Transfer</div>
    <div class="legend-item"><div class="legend-line legend-line--data" style="background:#6366f1;"></div> Indigo: Ingestion</div>
    <div class="legend-item"><div class="legend-line legend-line--data" style="background:#8b5cf6;"></div> Violet: ML/AI</div>
    <div class="legend-item"><div class="legend-line legend-line--data" style="background:#f59e0b;"></div> Amber: NLG</div>
    <div class="legend-item"><div class="legend-line legend-line--data" style="background:#0ea5e9;"></div> Sky: API</div>
    <div class="legend-item"><div class="legend-line legend-line--data" style="background:#10b981;"></div> Green: Deploy</div>
    <div class="legend-item"><div class="legend-line legend-line--data" style="background:#f43f5e;"></div> Rose: Frontend</div>
  </div>

  <!-- ═══════ FOOTER ═══════ -->
  <div class="bottom-bar">
    <span><span class="dot"></span>Production &mdash; ev-battery-health-prediction-system.vercel.app</span>
    <span>Flask 3.0 &bull; Python 3.12 &bull; Vercel Serverless &bull; SQLAlchemy &bull; NLP Project &bull; BIONS &bull; Oct 2026</span>
  </div>

</div>
</body>
</html>"""


def main():
    tmp = Path(tempfile.gettempdir())
    html_path = tmp / "arch_v2.html"
    png_path  = tmp / "arch_v2.png"
    html_path.write_text(HTML, encoding="utf-8")

    subprocess.run([
        CHROME,
        "--headless=new", "--no-sandbox", "--disable-gpu",
        "--force-device-scale-factor=2",
        "--window-size=1280,1350",
        f"--screenshot={png_path}",
        f"file:///{html_path}",
    ], capture_output=True)

    if not png_path.exists():
        print("ERROR: Chrome failed to render.")
        return

    im = Image.open(png_path)
    bg = Image.new(im.mode, im.size, im.getpixel((0, 0)))
    diff = ImageChops.difference(im, bg)
    bbox = diff.getbbox()
    if bbox:
        pad = 24
        crop_box = (max(0, bbox[0]-pad), max(0, bbox[1]-pad),
                     min(im.width, bbox[2]+pad), min(im.height, bbox[3]+pad))
        im = im.crop(crop_box)

    final = OUT_DIR / "system_architecture.png"
    im.save(final, "PNG", optimize=True)
    print(f"Saved: {final}  ({im.width}x{im.height})")

    if ARTIFACT_DIR.exists():
        shutil.copy2(final, ARTIFACT_DIR / "system_architecture.png")
        print("Copied to artifact dir")

if __name__ == "__main__":
    main()
