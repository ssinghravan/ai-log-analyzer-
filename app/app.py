"""
app/app.py
-----------
Flask Web Application for PUBLIC DEPLOYMENT (Render).

Features:
- Upload a .log file via browser
- AI analyzes it using Isolation Forest
- Displays results: Normal / Anomaly breakdown
- No Elasticsearch needed — standalone lightweight app

Deploy Command:
  gunicorn app.app:app
"""

import os
import sys
from flask import Flask, render_template, request, jsonify

# Allow importing utils and model from same folder
sys.path.insert(0, os.path.dirname(__file__))

from utils import read_log_file, logs_to_features, parse_log_line
from model import LogAnomalyDetector, keyword_detect

# ---- Flask App Setup ----
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "..", "static"),
)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # Max 5MB upload

ALLOWED_EXTENSIONS = {"log", "txt"}

def allowed_file(filename):
    """Check if uploaded file has a valid extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def analyze_log_content(content):
    """
    Core analysis function.
    Takes raw log text (string), returns analysis results dict.
    """
    # Parse each line from the uploaded content
    lines = content.decode("utf-8", errors="ignore").splitlines()
    parsed_logs = [parse_log_line(line) for line in lines]
    parsed_logs = [p for p in parsed_logs if p is not None]  # Remove None entries

    if not parsed_logs:
        return {"error": "No valid log lines found. Make sure the format is: YYYY-MM-DD HH:MM:SS LEVEL Message"}

    total = len(parsed_logs)
    errors = sum(1 for l in parsed_logs if l["level"] == "ERROR")
    warnings = sum(1 for l in parsed_logs if l["level"] == "WARNING")
    infos = total - errors - warnings

    # Try AI-based detection (needs at least 2 windows)
    features, windows = logs_to_features(parsed_logs, window_size=min(10, len(parsed_logs)))
    use_ai = len(features) >= 2

    anomaly_windows = 0
    anomaly_lines = []
    method = "keyword"

    if use_ai:
        detector = LogAnomalyDetector(contamination=0.15)
        detector.train(features)
        predictions = detector.predict(features)

        anomaly_windows = sum(1 for p in predictions if p == -1)
        method = "isolation_forest"

        # Collect sample anomaly lines for display
        for pred, window in zip(predictions, windows):
            if pred == -1:
                for log in window:
                    if log["level"] == "ERROR" and log not in anomaly_lines:
                        anomaly_lines.append(log)
                        if len(anomaly_lines) >= 5:
                            break

    else:
        # Fallback: keyword detection
        results = keyword_detect(parsed_logs)
        anomaly_windows = sum(1 for r in results if r == "ANOMALY")
        anomaly_lines = [
            log for log, res in zip(parsed_logs, results)
            if res == "ANOMALY" and log["level"] == "ERROR"
        ][:5]

    # Determine overall verdict
    anomaly_ratio = anomaly_windows / max(len(features) if use_ai else total, 1)
    if anomaly_ratio > 0.3:
        verdict = "CRITICAL"
        verdict_msg = "🚨 System is in a CRITICAL state! High anomaly rate detected."
    elif anomaly_ratio > 0.1 or errors > 3:
        verdict = "WARNING"
        verdict_msg = "⚠️ Anomalies detected. System needs attention."
    else:
        verdict = "NORMAL"
        verdict_msg = "✅ System looks healthy. No significant anomalies detected."

    return {
        "total": total,
        "infos": infos,
        "warnings": warnings,
        "errors": errors,
        "anomaly_windows": anomaly_windows,
        "total_windows": len(features) if use_ai else total,
        "anomaly_ratio": round(anomaly_ratio * 100, 1),
        "verdict": verdict,
        "verdict_msg": verdict_msg,
        "method": method,
        "sample_anomalies": [
            f"{l['timestamp']} {l['level']} — {l['message']}"
            for l in anomaly_lines
        ],
    }


@app.route("/")
def index():
    """Render the main upload page."""
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    """Handle file upload and return analysis results."""
    if "logfile" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files["logfile"]

    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Upload a .log or .txt file."}), 400

    content = file.read()
    result = analyze_log_content(content)

    return jsonify(result)


@app.route("/health")
def health():
    """Health check endpoint (for Render uptime monitoring)."""
    return jsonify({"status": "ok", "message": "AI Log Analyzer is running."})


if __name__ == "__main__":
    # Run locally for testing
    app.run(debug=True, host="0.0.0.0", port=5000)
