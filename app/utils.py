"""
app/utils.py
------------
Log parsing, time-window grouping, and feature extraction.
Supports multiple common log formats robustly.
"""

import re
from datetime import datetime, timedelta

# ── Supported log line patterns ───────────────────────────────────────────────
LOG_PATTERNS = [
    # 2024-01-15 10:30:00 ERROR Message  (standard)
    re.compile(
        r'^(\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2})(?:[,\.]\d+)?\s+'
        r'(ERROR|WARNING|WARN|INFO|DEBUG|CRITICAL)\s+(.+)$', re.IGNORECASE
    ),
    # [2024-01-15 10:30:00] ERROR Message  (bracketed)
    re.compile(
        r'^\[(\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2})(?:[,\.]\d+)?\]\s+'
        r'(ERROR|WARNING|WARN|INFO|DEBUG|CRITICAL)\s+(.+)$', re.IGNORECASE
    ),
    # 2024-01-15 10:30:00 app.module ERROR Message  (with logger name)
    re.compile(
        r'^(\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2})(?:[,\.]\d+)?\s+\S+\s+'
        r'(ERROR|WARNING|WARN|INFO|DEBUG|CRITICAL)\s+(.+)$', re.IGNORECASE
    ),
]

TIMESTAMP_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
]


def parse_log_line(line):
    """Parse a log line into a structured dict. Returns None on failure."""
    line = line.strip()
    if not line or line.startswith('#'):
        return None

    for pattern in LOG_PATTERNS:
        m = pattern.match(line)
        if m:
            ts_str, level, message = m.groups()
            level = level.upper()
            if level == "WARN":
                level = "WARNING"

            # Parse timestamp
            ts = None
            ts_clean = ts_str.strip().replace('T', ' ')
            for fmt in TIMESTAMP_FORMATS:
                try:
                    ts = datetime.strptime(ts_clean, fmt)
                    break
                except ValueError:
                    continue

            return {
                "timestamp": ts_str.strip(),
                "datetime": ts,
                "level": level,
                "message": message.strip(),
                "raw": line,
            }
    return None


def read_log_file(content_bytes):
    """Read and parse all valid log lines from uploaded file bytes."""
    lines = content_bytes.decode("utf-8", errors="ignore").splitlines()
    return [p for p in (parse_log_line(l) for l in lines) if p is not None]


def group_by_time_window(parsed_logs, window_seconds=60):
    """
    Group logs into fixed time windows.
    Falls back to fixed-size windows if no timestamps are available.
    Returns list of (label, [logs]) tuples.
    """
    dated = [l for l in parsed_logs if l["datetime"] is not None]

    if not dated:
        return _fixed_size_windows(parsed_logs, window_size=10)

    dated.sort(key=lambda x: x["datetime"])
    delta = timedelta(seconds=window_seconds)
    windows = []
    start = dated[0]["datetime"]
    current = []

    for log in dated:
        if log["datetime"] - start < delta:
            current.append(log)
        else:
            if current:
                windows.append((start.strftime("%H:%M:%S"), current))
            start = log["datetime"]
            current = [log]

    if current:
        windows.append((start.strftime("%H:%M:%S"), current))

    return windows


def _fixed_size_windows(logs, window_size=10):
    """Split logs into fixed-size windows (fallback when no timestamps)."""
    return [
        (f"W{i // window_size + 1}", logs[i:i + window_size])
        for i in range(0, len(logs), window_size)
        if logs[i:i + window_size]
    ]


def extract_features(windows):
    """
    Extract ML-ready feature vectors from log windows.

    Features per window (8 dimensions):
      [error_count, warning_count, critical_count, total_logs,
       error_ratio, warning_ratio, critical_ratio, avg_time_gap_seconds]
    """
    result = []
    for label, logs in windows:
        total = len(logs)
        if total == 0:
            continue

        error_count    = sum(1 for l in logs if l["level"] == "ERROR")
        warning_count  = sum(1 for l in logs if l["level"] == "WARNING")
        critical_count = sum(1 for l in logs if l["level"] == "CRITICAL")
        info_count     = total - error_count - warning_count - critical_count

        # Avg time gap between consecutive log entries (seconds)
        dated = [l for l in logs if l["datetime"] is not None]
        if len(dated) >= 2:
            gaps = [(dated[i+1]["datetime"] - dated[i]["datetime"]).total_seconds()
                    for i in range(len(dated) - 1)]
            avg_gap = round(sum(gaps) / len(gaps), 2)
        else:
            avg_gap = 0.0

        result.append({
            "label":          label,
            "total":          total,
            "error_count":    error_count,
            "warning_count":  warning_count,
            "critical_count": critical_count,
            "info_count":     info_count,
            "error_ratio":    round(error_count    / total, 4),
            "warning_ratio":  round(warning_count  / total, 4),
            "critical_ratio": round(critical_count / total, 4),
            "avg_time_gap":   avg_gap,
            # 8-dimensional feature vector for sklearn
            "vector": [
                error_count, warning_count, critical_count, total,
                round(error_count    / total, 4),
                round(warning_count  / total, 4),
                round(critical_count / total, 4),
                avg_gap,
            ],
        })

    return result
