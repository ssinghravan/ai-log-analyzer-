"""
app/app.py
-----------
Flask Dashboard — AI Log Anomaly Detection.
Returns enriched JSON: health classification, insights, recommendations.
"""

import os, sys
from collections import Counter
from flask import Flask, render_template, request, jsonify

sys.path.insert(0, os.path.dirname(__file__))

from utils import read_log_file, group_by_time_window, extract_features
from model import (LogAnomalyDetector, keyword_detect, explain_anomaly,
                   generate_insights, generate_recommendations, generate_health_summary)

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "..", "static"),
)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

ALLOWED_EXTENSIONS = {"log", "txt"}

def allowed_file(fn):
    return "." in fn and fn.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def analyze_log_content(content):
    """Full analysis pipeline — returns enriched result dict."""

    # ── 1. Parse ──────────────────────────────────────────────────────────────
    parsed_logs = read_log_file(content)
    if not parsed_logs:
        return {"error": "No valid log lines found. "
                         "Expected: YYYY-MM-DD HH:MM:SS LEVEL Message"}

    total     = len(parsed_logs)
    errors    = sum(1 for l in parsed_logs if l["level"] == "ERROR")
    warnings  = sum(1 for l in parsed_logs if l["level"] == "WARNING")
    criticals = sum(1 for l in parsed_logs if l["level"] == "CRITICAL")
    infos     = total - errors - warnings - criticals

    # Top error type extraction
    error_msgs = [l["message"] for l in parsed_logs if l["level"] in ("ERROR", "CRITICAL")]
    top_error_type = Counter(error_msgs).most_common(1)[0][0] if error_msgs else "None"

    # ── 2. System health (error-ratio based) ─────────────────────────────────
    error_ratio = round(errors / max(total, 1), 4)
    if error_ratio < 0.4:
        system_health = "HEALTHY"
    elif error_ratio < 0.8:
        system_health = "WARNING"
    else:
        system_health = "CRITICAL"

    # ── 3. Time windows & feature extraction ─────────────────────────────────
    windows      = group_by_time_window(parsed_logs, window_seconds=60)
    feature_data = extract_features(windows)
    vectors      = [f["vector"] for f in feature_data]

    # ── 4. ML Detection ───────────────────────────────────────────────────────
    method      = "keyword"
    predictions = []
    scores      = []
    threshold   = None
    confidence  = None

    if len(vectors) >= 2:
        # Dynamic contamination: higher error ratio → expect more anomalies
        contamination = max(0.05, min(0.25, error_ratio))
        detector = LogAnomalyDetector(contamination=contamination)
        detector.train(vectors)
        predictions, scores = detector.predict(vectors)
        threshold  = detector.threshold
        confidence = detector.model_confidence()
        method     = "isolation_forest"
    else:
        kw = keyword_detect(parsed_logs)
        predictions = [-1 if r == "ANOMALY" else 1 for r in kw]
        scores      = [-1.0 if r == "ANOMALY" else 0.0 for r in kw]

    # ── 5. Window data ────────────────────────────────────────────────────────
    window_data   = []
    anomaly_count = 0

    if method == "isolation_forest":
        for feat, pred, score in zip(feature_data, predictions, scores):
            is_anom = (pred == -1)
            if is_anom:
                anomaly_count += 1
            window_data.append({
                "label":     feat["label"],
                "total":     feat["total"],
                "errors":    feat["error_count"],
                "warnings":  feat["warning_count"],
                "infos":     feat["info_count"],
                "criticals": feat["critical_count"],
                "is_anomaly": is_anom,
                "score":     round(score, 4),
                "reason":    explain_anomaly(feat) if is_anom else "",
            })
    else:
        for log, pred in zip(parsed_logs, predictions):
            is_anom = (pred == -1)
            if is_anom:
                anomaly_count += 1
            window_data.append({
                "label": log["timestamp"], "total": 1,
                "errors":    1 if log["level"] == "ERROR" else 0,
                "warnings":  1 if log["level"] == "WARNING" else 0,
                "infos":     1 if log["level"] == "INFO" else 0,
                "criticals": 1 if log["level"] == "CRITICAL" else 0,
                "is_anomaly": is_anom, "score": -1.0 if is_anom else 0.0,
                "reason": "Keyword match" if is_anom else "",
            })

    total_windows = len(window_data)
    anomaly_rate  = round((anomaly_count / max(total_windows, 1)) * 100, 1)

    # ── 6. Verdict ────────────────────────────────────────────────────────────
    if anomaly_count == 0 and system_health == "HEALTHY":
        verdict     = "NORMAL"
        verdict_msg = "No anomalies detected. System is stable."
    elif anomaly_count == 0 and system_health in ("WARNING", "CRITICAL"):
        verdict     = system_health
        verdict_msg = (f"No statistical anomalies, but high error rate "
                       f"({error_ratio*100:.0f}%) — system needs review.")
    elif anomaly_count > 0 and system_health == "CRITICAL":
        verdict     = "CRITICAL"
        verdict_msg = "Anomalies detected with critical error rate. Immediate action required."
    else:
        verdict     = "WARNING"
        verdict_msg = "Anomalies detected. System needs attention."

    # ── 7. Sample anomaly lines ───────────────────────────────────────────────
    sample_anomalies = [
        f"{l['timestamp']}  [{l['level']}]  {l['message']}"
        for l in parsed_logs
        if l["level"] in ("ERROR", "CRITICAL")
    ][:8]

    # ── 8. Assemble result ────────────────────────────────────────────────────
    result = {
        "total":           total,
        "infos":           infos,
        "warnings":        warnings,
        "errors":          errors,
        "criticals":       criticals,
        "error_ratio":     error_ratio,
        "error_ratio_pct": round(error_ratio * 100, 1),
        "system_health":   system_health,
        "top_error_type":  top_error_type,
        "anomaly_windows": anomaly_count,
        "total_windows":   total_windows,
        "anomaly_rate":    anomaly_rate,
        "verdict":         verdict,
        "verdict_msg":     verdict_msg,
        "method":          method,
        "threshold":       round(threshold, 4) if threshold is not None else None,
        "confidence":      confidence,
        "window_data":     window_data,
        "sample_anomalies": sample_anomalies,
        "log_lines": [
            {"timestamp": l["timestamp"], "level": l["level"], "message": l["message"]}
            for l in parsed_logs
        ],
    }

    # ── 9. Insights & recommendations ─────────────────────────────────────────
    result["insights"]        = generate_insights(result)
    result["recommendations"] = generate_recommendations(result)
    result["health_summary"]  = generate_health_summary(result)

    return result


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    if "logfile" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400
    file = request.files["logfile"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Upload .log or .txt"}), 400
    result = analyze_log_content(file.read())
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/health")
def health_check():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
