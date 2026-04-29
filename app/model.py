"""
app/model.py
-------------
AI Anomaly Detection using Isolation Forest.

Isolation Forest is an unsupervised ML algorithm that detects anomalies
by "isolating" data points. Anomalies are isolated faster (fewer splits needed).
It works WITHOUT labeled training data — perfect for log analysis!
"""

import numpy as np
from sklearn.ensemble import IsolationForest


class LogAnomalyDetector:
    """
    Trainable anomaly detector for log feature windows.
    Uses scikit-learn's IsolationForest under the hood.
    """

    def __init__(self, contamination=0.1):
        """
        contamination: expected % of anomalies in data (0.1 = 10%).
        You can tune this value based on your logs.
        """
        self.model = IsolationForest(
            contamination=contamination,  # Expected anomaly rate
            random_state=42,             # For reproducible results
            n_estimators=100,            # Number of trees in the forest
        )
        self.is_trained = False

    def train(self, features):
        """
        Train the model on feature vectors.
        features: list of [error_count, warning_count, error_ratio]
        Isolation Forest learns what "normal" looks like.
        """
        if len(features) == 0:
            raise ValueError("No features to train on. Check your log file.")

        X = np.array(features)
        self.model.fit(X)
        self.is_trained = True
        print(f"[✓] Model trained on {len(features)} log windows.")

    def predict(self, features):
        """
        Predict anomalies for a list of feature windows.

        Returns: list of labels where:
            -1 → ANOMALY
             1 → NORMAL
        """
        if not self.is_trained:
            raise RuntimeError("Model is not trained yet. Call train() first.")

        X = np.array(features)
        predictions = self.model.predict(X)  # Returns 1 or -1 for each window
        return predictions

    def predict_single(self, feature_vector):
        """
        Predict a single log window.
        feature_vector: [error_count, warning_count, error_ratio]
        Returns: "ANOMALY" or "NORMAL"
        """
        if not self.is_trained:
            raise RuntimeError("Model is not trained yet. Call train() first.")

        X = np.array([feature_vector])
        result = self.model.predict(X)[0]
        return "ANOMALY" if result == -1 else "NORMAL"


def keyword_detect(parsed_logs):
    """
    Simple backup method: keyword-based anomaly detection.
    Flags a log as anomaly if it contains suspicious keywords.
    No AI needed — good for demonstration / comparison.
    """
    DANGER_KEYWORDS = [
        "error", "exception", "failed", "crash", "unavailable",
        "timeout", "overflow", "unauthorized", "critical", "fatal"
    ]

    results = []
    for log in parsed_logs:
        msg_lower = log["message"].lower()
        level = log["level"]

        # Check if level is ERROR or message has danger keyword
        is_anomaly = (
            level == "ERROR" or
            any(kw in msg_lower for kw in DANGER_KEYWORDS)
        )
        results.append("ANOMALY" if is_anomaly else "NORMAL")

    return results
