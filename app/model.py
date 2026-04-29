"""
app/model.py
-------------
Isolation Forest anomaly detector with:
- StandardScaler normalization
- Dynamic contamination tuning
- Anomaly confidence score
- Human-readable explanations
"""

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


class LogAnomalyDetector:
    """Production-grade log anomaly detector using Isolation Forest."""

    def __init__(self, contamination=0.05):
        self.contamination = contamination
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=150,
            max_samples="auto",
        )
        self.scaler    = StandardScaler()
        self.is_trained = False
        self.threshold  = None
        self._scores    = []

    def train(self, feature_vectors):
        """Normalize and fit model. Computes score threshold."""
        if len(feature_vectors) < 2:
            raise ValueError(
                "Need at least 2 log windows to train. "
                "Upload a larger log file (at least 20 lines)."
            )
        X = np.array(feature_vectors, dtype=float)
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self.is_trained = True
        self._scores   = self.model.score_samples(X_scaled).tolist()
        self.threshold = float(np.percentile(
            self._scores, max(5, int(self.contamination * 100))
        ))
        print(f"[OK] Trained on {len(feature_vectors)} windows. "
              f"Threshold: {self.threshold:.4f}")

    def predict(self, feature_vectors):
        """
        Returns:
          predictions : list of -1 (anomaly) or 1 (normal)
          scores      : list of floats — lower = more anomalous
        """
        if not self.is_trained:
            raise RuntimeError("Call train() first.")
        X = np.array(feature_vectors, dtype=float)
        X_scaled    = self.scaler.transform(X)
        predictions = self.model.predict(X_scaled).tolist()
        scores      = self.model.score_samples(X_scaled).tolist()
        return predictions, scores

    def model_confidence(self):
        """
        Returns 0–100 confidence score.
        Higher = model is more certain about its predictions.
        Based on spread of anomaly scores.
        """
        if not self._scores:
            return 0.0
        mn, mx = min(self._scores), max(self._scores)
        if mx == mn:
            return 50.0
        spread = mx - mn
        # Wider spread = more confident separation of normal vs anomaly
        confidence = min(100.0, round(spread * 150, 1))
        return confidence


def explain_anomaly(window):
    """Plain-English explanation for an anomalous window."""
    reasons = []
    if window["critical_count"] > 0:
        reasons.append(f"{window['critical_count']} CRITICAL event(s)")
    if window["error_ratio"] > 0.4:
        reasons.append(f"High error rate ({window['error_ratio']*100:.0f}%)")
    elif window["error_count"] > 3:
        reasons.append(f"Error spike: {window['error_count']} errors")
    if window["warning_ratio"] > 0.5:
        reasons.append(f"Excessive warnings ({window['warning_ratio']*100:.0f}%)")
    if window["total"] > 80:
        reasons.append(f"Unusual log volume ({window['total']} entries)")
    if not reasons:
        reasons.append("Statistical outlier detected by Isolation Forest")
    return "; ".join(reasons)


def generate_insights(d):
    """Generate actionable insight strings based on analysis result."""
    insights = []
    er  = d["error_ratio"]
    aw  = d["anomaly_windows"]
    err = d["errors"]
    tot = d["total"]
    sh  = d["system_health"]

    if er >= 0.8:
        insights.append(
            f"Critical error rate: {er*100:.0f}% of logs ({err}/{tot}) are errors "
            f"— possible system crash, DB failure, or misconfiguration."
        )
    elif er >= 0.4:
        insights.append(
            f"High error rate: {er*100:.0f}% — system showing signs of stress. "
            f"Review recent deployments or config changes."
        )

    if aw == 0 and er >= 0.4:
        insights.append(
            "No statistical anomaly pattern detected, but the elevated error rate "
            "may indicate slow-burn failures not yet forming a clear pattern."
        )
    elif aw > 0:
        insights.append(
            f"{aw} anomalous time window(s) detected with abnormal error/warning "
            f"frequency. Likely caused by a traffic spike, failure cascade, or restart loop."
        )

    if d["warnings"] > d["errors"] * 2:
        insights.append(
            "Warning count exceeds errors by 2×. Repeated warnings often precede "
            "service degradation — consider treating them as soft errors."
        )

    if not insights:
        insights.append(
            "System appears healthy. No significant patterns of concern detected."
        )

    return insights


def generate_recommendations(d):
    """Generate concrete action recommendations."""
    recs = []
    er = d["error_ratio"]
    aw = d["anomaly_windows"]

    if er >= 0.8:
        recs += [
            "Immediately inspect database connection pool and service health endpoints.",
            "Review application logs for stack traces and exception root causes.",
            "Check system resources — CPU, memory, and disk I/O.",
            "Consider rolling back the latest deployment if errors started after a release.",
        ]
    elif er >= 0.4:
        recs += [
            "Review error logs for recurring patterns or repeated failures.",
            "Check for misconfiguration in recently deployed services.",
            "Set up automated alerting thresholds for error rates above 20%.",
        ]
    elif aw > 0:
        recs += [
            "Investigate the anomalous time windows shown in the Charts tab.",
            "Cross-reference flagged windows with deployment events or traffic spikes.",
            "Enable distributed tracing (e.g., Jaeger/Zipkin) for deeper root-cause analysis.",
        ]
    else:
        recs.append("No immediate actions required. Continue routine log monitoring.")

    return recs


def generate_health_summary(d):
    """Intelligent health summary — context-aware, not generic."""
    er  = d["error_ratio"]
    aw  = d["anomaly_windows"]
    tot = d["total"]
    err = d["errors"]
    wrn = d["warnings"]
    sh  = d["system_health"]
    tw  = d["total_windows"]

    if aw == 0 and er >= 0.8:
        return (
            f"No statistical anomaly pattern detected, but the system is in a "
            f"CRITICAL state with a {er*100:.0f}% error rate ({err} errors out of "
            f"{tot} logs). This strongly indicates a system crash, database failure, "
            f"or severe misconfiguration. Immediate investigation is required."
        )
    elif aw == 0 and er >= 0.4:
        return (
            f"No statistical anomalies found, but the system shows a high error "
            f"rate of {er*100:.0f}% ({err} errors / {tot} logs). This may indicate "
            f"underlying issues that have not yet formed a detectable anomaly pattern. "
            f"Monitor closely and review recent changes."
        )
    elif aw == 0 and er < 0.4:
        return (
            f"System is healthy. Analyzed {tot} log entries across {tw} time "
            f"window(s) — no anomalies detected. Error rate is {er*100:.0f}%, "
            f"well within acceptable range."
        )
    elif aw > 0 and er >= 0.8:
        return (
            f"System is in CRITICAL condition. Detected {aw}/{tw} anomalous "
            f"window(s) with a {er*100:.0f}% error rate. Spike patterns suggest "
            f"a cascading failure or service crash. Immediate action required."
        )
    else:
        return (
            f"System needs attention. Detected {aw}/{tw} anomalous window(s) "
            f"with unusual patterns. Error rate: {er*100:.0f}% ({err} errors, "
            f"{wrn} warnings out of {tot} logs). Review flagged windows."
        )


def keyword_detect(parsed_logs):
    """Keyword-based fallback for very small log files."""
    DANGER = [
        "exception", "failed", "crash", "unavailable", "timeout",
        "overflow", "unauthorized", "fatal", "panic", "traceback",
    ]
    results = []
    for log in parsed_logs:
        is_anomaly = (
            log["level"] == "CRITICAL" or
            any(kw in log["message"].lower() for kw in DANGER)
        )
        results.append("ANOMALY" if is_anomaly else "NORMAL")
    return results
