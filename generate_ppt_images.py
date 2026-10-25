import os
import sys
import tempfile
import subprocess
import shutil
from pathlib import Path
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
PPT_DIR = SCRIPT_DIR / "ppt_images"
PPT_DIR.mkdir(parents=True, exist_ok=True)

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TEMP_DIR = Path(tempfile.gettempdir())

HTML_BOILERPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}
body {
    background-color: #0c101a;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #f2f5fb;
    padding: 24px;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    min-height: 100vh;
}
.widget-card {
    background: #131724;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 24px;
    width: 600px;
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6);
}
.widget-header {
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding-bottom: 16px;
    margin-bottom: 20px;
}
.widget-header h3 {
    font-size: 1.25rem;
    font-weight: 700;
    color: #ffffff;
    display: flex;
    align-items: center;
    gap: 8px;
}
.widget-header p {
    font-size: 0.85rem;
    color: #8e95ab;
    margin-top: 4px;
}
.nlg-pill {
    background: rgba(88, 208, 122, 0.15);
    color: #58d07a;
    border: 1px solid rgba(88, 208, 122, 0.3);
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
}
.form-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    margin-bottom: 20px;
}
.form-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
}
.form-group.full-width {
    grid-column: span 2;
}
.form-label {
    font-size: 0.78rem;
    font-weight: 600;
    color: #8e95ab;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.form-input {
    background: #1a1f2d;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    padding: 10px 14px;
    color: #ffffff;
    font-size: 0.95rem;
    font-weight: 600;
    font-family: inherit;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.form-input .unit {
    color: #58d07a;
    font-size: 0.82rem;
    font-weight: 500;
}
.btn-primary {
    background: linear-gradient(135deg, #22c55e, #16a34a);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 12px 20px;
    font-size: 0.95rem;
    font-weight: 700;
    width: 100%;
    cursor: pointer;
    box-shadow: 0 4px 14px rgba(34, 197, 94, 0.4);
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 8px;
}
.status-bar {
    margin-top: 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 8px;
    font-size: 0.78rem;
    color: #8e95ab;
}
.status-indicator {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #58d07a;
    box-shadow: 0 0 8px #58d07a;
    margin-right: 6px;
}

/* Report Styles */
.ribbon {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 16px;
    flex-wrap: wrap;
}
.badge-warning {
    background: rgba(245, 158, 11, 0.2);
    border: 1px solid rgba(245, 158, 11, 0.5);
    color: #fbbf24;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.5px;
}
.meta-pill {
    background: #1a1f2d;
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: #8e95ab;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.75rem;
}
.meta-time {
    margin-left: auto;
    color: #64748b;
    font-size: 0.75rem;
}
.section-title {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.8px;
    color: #64748b;
    text-transform: uppercase;
    margin-bottom: 8px;
}
.summary-box {
    background: #1a1f2d;
    border-left: 3px solid #f59e0b;
    border-radius: 8px;
    padding: 14px 16px;
    font-size: 0.88rem;
    line-height: 1.55;
    color: #cbd5e1;
    margin-bottom: 18px;
}
.summary-box strong {
    color: #ffffff;
}
.readings-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
}
.reading-tile {
    background: #1a1f2d;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 8px;
    padding: 10px 12px;
}
.reading-tile.highlight {
    background: rgba(88, 208, 122, 0.08);
    border-color: rgba(88, 208, 122, 0.3);
}
.reading-tile__label {
    display: block;
    font-size: 0.72rem;
    color: #8e95ab;
    margin-bottom: 4px;
}
.reading-tile__val {
    font-size: 1.05rem;
    font-weight: 700;
    color: #ffffff;
}
.reading-tile.highlight .reading-tile__val {
    color: #58d07a;
}

/* Findings & Actions */
.finding-card {
    background: #1a1f2d;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    padding: 14px;
    margin-bottom: 12px;
}
.finding-card.severity-high {
    border-left: 4px solid #ef4444;
}
.finding-card.severity-mod {
    border-left: 4px solid #f59e0b;
}
.finding-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
}
.severity-pill-high {
    background: rgba(239, 68, 68, 0.2);
    color: #f87171;
    border: 1px solid rgba(239, 68, 68, 0.3);
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 0.68rem;
    font-weight: 700;
}
.severity-pill-mod {
    background: rgba(245, 158, 11, 0.2);
    color: #fbbf24;
    border: 1px solid rgba(245, 158, 11, 0.3);
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 0.68rem;
    font-weight: 700;
}
.finding-title {
    font-size: 0.92rem;
    font-weight: 700;
    color: #ffffff;
}
.finding-desc {
    font-size: 0.82rem;
    color: #94a3b8;
    line-height: 1.45;
    margin-bottom: 8px;
}
.evidence-chips {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.74rem;
}
.chip {
    background: #0f1320;
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #38bdf8;
    padding: 2px 8px;
    border-radius: 4px;
    font-family: monospace;
}
.chip-caption {
    color: #64748b;
    font-style: italic;
}
.action-card {
    background: rgba(34, 197, 94, 0.08);
    border: 1px solid rgba(34, 197, 94, 0.25);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 0.84rem;
    color: #86efac;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
}
.limitations-box {
    background: #0f1320;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 8px;
    padding: 12px 16px;
}
.limitations-list {
    list-style-type: none;
    font-size: 0.78rem;
    color: #94a3b8;
    line-height: 1.6;
}
.limitations-list li::before {
    content: "•";
    color: #64748b;
    margin-right: 8px;
}
</style>
</head>
<body>
{CONTENT}
</body>
</html>
"""

BOX1_HTML = """
<div class="widget-card">
    <div class="widget-header">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h3>Prediction Configuration</h3>
            <span class="nlg-pill">Live Telemetry Ingest</span>
        </div>
        <p>Run a real-time battery health assessment and diagnostic scan</p>
    </div>
    
    <div class="form-grid">
        <div class="form-group">
            <span class="form-label">Battery Voltage</span>
            <div class="form-input">
                <span>600.0</span>
                <span class="unit">V</span>
            </div>
        </div>
        <div class="form-group">
            <span class="form-label">Battery Current</span>
            <div class="form-input">
                <span>30.0</span>
                <span class="unit">A</span>
            </div>
        </div>
        <div class="form-group">
            <span class="form-label">State of Charge (SOC)</span>
            <div class="form-input">
                <span>83.0</span>
                <span class="unit">%</span>
            </div>
        </div>
        <div class="form-group">
            <span class="form-label">Battery Temperature</span>
            <div class="form-input">
                <span>45.0</span>
                <span class="unit">°C</span>
            </div>
        </div>
        <div class="form-group full-width">
            <span class="form-label">Degradation Level</span>
            <div class="form-input">
                <span>30.0</span>
                <span class="unit">% Index</span>
            </div>
        </div>
    </div>
    
    <button class="btn-primary" type="button">
        ⚡ Run Prediction & Diagnostic Scan
    </button>
    
    <div class="status-bar">
        <div><span class="status-indicator"></span>Ready for sensor input</div>
        <div>Model: Hybrid LSTM-RNN / HEURISTIC</div>
    </div>
</div>
"""

BOX2_HTML = """
<div class="widget-card">
    <div class="widget-header">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h3>Diagnostic Report</h3>
            <span class="nlg-pill">NLG: Context-Aware</span>
        </div>
        <p>Plain-English, evidence-grounded explanation of the latest prediction</p>
    </div>
    
    <div class="ribbon">
        <span class="badge-warning">WARNING</span>
        <span class="meta-pill">Report #01</span>
        <span class="meta-pill">Record #104</span>
        <span class="meta-time">Oct 25, 07:28 PM</span>
    </div>
    
    <div class="section-title">Summary</div>
    <div class="summary-box">
        The prediction indicates that the battery condition needs attention (<strong>Warning</strong>). The health score is <strong>76.41%</strong>. Key observations: measured temperature of <strong>45.0 °C</strong> crosses the high-temperature rule; pack voltage is abnormal at <strong>600.0 V</strong>; degradation index is elevated at <strong>30.0</strong>. The report flags these measurements for review; it does not confirm an internal battery fault.
    </div>
    
    <div class="section-title">Telemetry Readings</div>
    <div class="readings-grid">
        <div class="reading-tile">
            <span class="reading-tile__label">Voltage</span>
            <strong class="reading-tile__val">600 V</strong>
        </div>
        <div class="reading-tile">
            <span class="reading-tile__label">Current</span>
            <strong class="reading-tile__val">30 A</strong>
        </div>
        <div class="reading-tile">
            <span class="reading-tile__label">SOC</span>
            <strong class="reading-tile__val">83 %</strong>
        </div>
        <div class="reading-tile">
            <span class="reading-tile__label">Temperature</span>
            <strong class="reading-tile__val">45 °C</strong>
        </div>
        <div class="reading-tile">
            <span class="reading-tile__label">Pack Power</span>
            <strong class="reading-tile__val">18 kW</strong>
        </div>
        <div class="reading-tile highlight">
            <span class="reading-tile__label">Health Score</span>
            <strong class="reading-tile__val">76.4 %</strong>
        </div>
    </div>
</div>
"""

BOX3_HTML = """
<div class="widget-card">
    <div class="widget-header">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h3>Findings & Operational Actions</h3>
            <span class="nlg-pill">Facts-First Grounding</span>
        </div>
        <p>Review evidence, severity rules, and recommended mitigation</p>
    </div>
    
    <div class="section-title">Key Findings</div>
    <div class="finding-card severity-high">
        <div class="finding-header">
            <span class="severity-pill-high">HIGH</span>
            <span class="finding-title">Elevated Pack Temperature</span>
        </div>
        <div class="finding-desc">
            The measured temperature of 45.0 °C crosses the prototype rule used for high-temperature concern (threshold: 42.0 °C).
        </div>
        <div class="evidence-chips">
            <span class="chip">temp: 45 °C</span>
            <span class="chip-caption">Advisory flag; check cooling circuit</span>
        </div>
    </div>
    
    <div class="finding-card severity-mod">
        <div class="finding-header">
            <span class="severity-pill-mod">MODERATE</span>
            <span class="finding-title">Abnormal Pack Voltage</span>
        </div>
        <div class="finding-desc">
            The pack voltage (600.0 V) falls outside the project default nominal operating band (280.0 V to 450.0 V).
        </div>
        <div class="evidence-chips">
            <span class="chip">voltage: 600 V</span>
            <span class="chip-caption">Verify bus sensor and inverter status</span>
        </div>
    </div>
    
    <div class="section-title">Recommended Action</div>
    <div class="action-card">
        <span>🔧</span>
        <div>Schedule thermal management check: inspect cooling loops, thermal interface material, and pack blower.</div>
    </div>
    
    <div class="section-title">Limitations & Boundary Notice</div>
    <div class="limitations-box">
        <ul class="limitations-list">
            <li>Decision-support summary: does not replace certified manufacturer inspection.</li>
            <li>Thresholds used are prototype defaults, not warranty limit specs.</li>
            <li>Degradation level is treated as a 0-100 index, not direct capacity loss %.</li>
        </ul>
    </div>
</div>
"""

CARDS = [
    ("box1_prediction_input.png", BOX1_HTML, 660, 620),
    ("box2_generated_report.png", BOX2_HTML, 660, 620),
    ("box3_findings_and_actions.png", BOX3_HTML, 660, 680),
]

def render_cards():
    for filename, content, width, height in CARDS:
        html_code = HTML_BOILERPLATE.replace("{CONTENT}", content)
        temp_html = TEMP_DIR / f"temp_{filename}.html"
        temp_png = TEMP_DIR / f"temp_{filename}.png"
        
        with open(temp_html, "w", encoding="utf-8") as f:
            f.write(html_code)
            
        cmd = [
            CHROME_PATH,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--force-device-scale-factor=2",
            f"--window-size={width},{height}",
            f"--screenshot={temp_png}",
            f"file:///{temp_html}"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if not temp_png.exists():
            print(f"Failed to render {filename}: {res.stderr}")
            continue
            
        # Crop to content cleanly with Pillow
        im = Image.open(temp_png)
        # Crop border padding to focus tightly on the card
        # The body has 24px padding at scale 2x = 48px
        # We can auto-crop or crop with tight bounding box
        bbox = im.getbbox()
        target_path = PPT_DIR / filename
        im.save(target_path, "PNG", optimize=True)
        print(f"Rendered {filename} -> {target_path} (Size: {im.size})")

        # Also copy to artifact directory
        artifact_dir = Path(r"C:\Users\User\.gemini\antigravity\brain\e0a4c102-950e-44bf-b048-732a071e0012")
        if artifact_dir.exists():
            shutil.copy2(target_path, artifact_dir / filename)
            print(f"Copied to artifact dir: {artifact_dir / filename}")

if __name__ == "__main__":
    render_cards()
