"""
app/utils.py
-------------
Utility functions for parsing log files.
Converts raw log text into numerical features for the AI model.
"""

import re
from datetime import datetime


# Regex pattern to parse a standard log line
# Example: "2024-01-15 10:00:25 ERROR Failed to connect..."
LOG_PATTERN = re.compile(
    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+(INFO|WARNING|ERROR)\s+(.*)"
)

def parse_log_line(line):
    """
    Parses a single log line into its parts.
    Returns a dict with 'timestamp', 'level', 'message' or None if invalid.
    """
    line = line.strip()
    if not line:
        return None

    match = LOG_PATTERN.match(line)
    if not match:
        return None  # Skip lines that don't match the format

    timestamp_str, level, message = match.groups()

    return {
        "timestamp": timestamp_str,
        "level": level,
        "message": message,
    }


def read_log_file(filepath):
    """
    Reads a log file and returns a list of parsed log dicts.
    Invalid/empty lines are skipped automatically.
    """
    parsed_logs = []
    try:
        with open(filepath, "r") as f:
            for line in f:
                parsed = parse_log_line(line)
                if parsed:
                    parsed_logs.append(parsed)
    except FileNotFoundError:
        print(f"[ERROR] Log file not found: {filepath}")
    return parsed_logs


def logs_to_features(parsed_logs, window_size=10):
    """
    Converts parsed logs into feature windows for the AI model.

    How it works:
    - We look at every window of `window_size` consecutive log lines.
    - For each window, we count:
        * Number of ERROR logs
        * Number of WARNING logs
        * Ratio of errors to total logs
    - These 3 numbers become the "features" the AI model learns from.

    Returns:
        features  → list of [error_count, warning_count, error_ratio]
        windows   → the original log lines in each window (for display)
    """
    features = []
    windows = []

    if len(parsed_logs) < window_size:
        window_size = len(parsed_logs)  # Handle small log files

    for i in range(len(parsed_logs) - window_size + 1):
        window = parsed_logs[i : i + window_size]

        error_count = sum(1 for log in window if log["level"] == "ERROR")
        warning_count = sum(1 for log in window if log["level"] == "WARNING")
        total = len(window)
        error_ratio = error_count / total if total > 0 else 0

        features.append([error_count, warning_count, error_ratio])
        windows.append(window)

    return features, windows
