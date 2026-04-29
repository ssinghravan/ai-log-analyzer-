"""
analyzer.py
------------
LOCAL FULL-SYSTEM ANALYZER
Reads logs, extracts features, runs AI model, and prints alerts.
This is the main script for the local DevOps monitoring setup.

Run: python analyzer.py
  or: python analyzer.py --file logs/custom.log
"""

import sys
import os
import argparse
from datetime import datetime

# Add app/ to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from utils import read_log_file, logs_to_features
from model import LogAnomalyDetector, keyword_detect


# ---- Configuration ----
DEFAULT_LOG_FILE = os.path.join("logs", "sample.log")
WINDOW_SIZE = 10           # Analyze logs in groups of 10
ANOMALY_THRESHOLD = 3      # Alert if 3+ anomaly windows in a row

# ---- ANSI colors for terminal output ----
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_banner():
    print(f"""
{CYAN}{BOLD}╔══════════════════════════════════════════════════╗
║     AI-Powered Log Analyzer (AIOps Project)      ║
║     Anomaly Detection with Isolation Forest      ║
╚══════════════════════════════════════════════════╝{RESET}
""")


def print_alert(message, level="ERROR"):
    """Prints a formatted alert to console."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    icon = "🚨" if level == "ERROR" else "⚠️"
    color = RED if level == "ERROR" else YELLOW
    print(f"{color}{BOLD}[ALERT] {icon} {timestamp} — {message}{RESET}")


def analyze_logs(log_file=DEFAULT_LOG_FILE, use_ai=True):
    """
    Main analysis pipeline:
    1. Read and parse log file
    2. Extract features using sliding window
    3. Train AI model (Isolation Forest)
    4. Predict anomalies
    5. Print results and alerts
    """
    print_banner()
    print(f"[*] Analyzing log file: {log_file}\n")

    # Step 1: Parse logs
    parsed_logs = read_log_file(log_file)
    if not parsed_logs:
        print(f"{RED}[!] No valid logs found in {log_file}{RESET}")
        return

    total = len(parsed_logs)
    errors = sum(1 for l in parsed_logs if l["level"] == "ERROR")
    warnings = sum(1 for l in parsed_logs if l["level"] == "WARNING")
    infos = total - errors - warnings

    print(f"{'='*55}")
    print(f"  📄 Total Log Lines : {total}")
    print(f"  ✅ INFO            : {GREEN}{infos}{RESET}")
    print(f"  ⚠️  WARNING         : {YELLOW}{warnings}{RESET}")
    print(f"  ❌ ERROR           : {RED}{errors}{RESET}")
    print(f"{'='*55}\n")

    if use_ai:
        # Step 2: Extract features using sliding windows
        features, windows = logs_to_features(parsed_logs, window_size=WINDOW_SIZE)

        if len(features) < 2:
            print(f"{YELLOW}[!] Not enough logs for AI. Falling back to keyword detection.{RESET}")
            use_ai = False
        else:
            # Step 3: Train AI model
            detector = LogAnomalyDetector(contamination=0.15)
            detector.train(features)

            # Step 4: Predict anomalies
            predictions = detector.predict(features)

            print(f"[*] AI Analysis Complete — {WINDOW_SIZE}-line sliding window\n")

            anomaly_count = 0
            consecutive_anomalies = 0

            for i, (pred, window) in enumerate(zip(predictions, windows)):
                if pred == -1:  # Anomaly detected
                    anomaly_count += 1
                    consecutive_anomalies += 1
                    first_line = window[0]
                    print(f"  {RED}[ANOMALY]{RESET} Window {i+1:03d} | "
                          f"Starting at: {first_line['timestamp']} | "
                          f"Errors in window: {sum(1 for l in window if l['level']=='ERROR')}")

                    # Trigger alert if anomalies keep stacking
                    if consecutive_anomalies >= ANOMALY_THRESHOLD:
                        print_alert(
                            f"High anomaly burst detected at window {i+1}! "
                            f"{consecutive_anomalies} consecutive anomaly windows.",
                            level="ERROR"
                        )
                else:
                    consecutive_anomalies = 0  # Reset counter on normal window

            print(f"\n{'='*55}")
            print(f"  🔍 Windows Analyzed : {len(predictions)}")
            print(f"  🚨 Anomaly Windows  : {RED}{anomaly_count}{RESET}")
            print(f"  ✅ Normal Windows   : {GREEN}{len(predictions) - anomaly_count}{RESET}")
            print(f"{'='*55}\n")

            # Final verdict
            anomaly_ratio = anomaly_count / len(predictions)
            if anomaly_ratio > 0.3:
                print_alert(
                    f"CRITICAL: {anomaly_ratio*100:.1f}% of log windows are anomalous! "
                    "Immediate investigation required.",
                    level="ERROR"
                )
            elif anomaly_ratio > 0.1:
                print_alert(
                    f"WARNING: {anomaly_ratio*100:.1f}% anomaly rate detected. "
                    "Monitor the system closely.",
                    level="WARNING"
                )
            else:
                print(f"  {GREEN}✅ System looks HEALTHY. Low anomaly rate: {anomaly_ratio*100:.1f}%{RESET}\n")

    if not use_ai:
        # Fallback: Keyword-based detection
        print("[*] Using keyword-based detection (no AI)...\n")
        results = keyword_detect(parsed_logs)
        anomalies = [(log, res) for log, res in zip(parsed_logs, results) if res == "ANOMALY"]

        for log, _ in anomalies[:10]:  # Show first 10
            print(f"  {RED}[ANOMALY]{RESET} {log['timestamp']} {log['level']} — {log['message']}")

        if len(anomalies) > errors:
            print_alert(
                f"High number of ERROR logs detected → {errors} ERRORs found! Alert!",
                level="ERROR"
            )

    print("\n[✓] Analysis complete.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Log Analyzer")
    parser.add_argument(
        "--file",
        default=DEFAULT_LOG_FILE,
        help="Path to the log file to analyze"
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Use keyword detection instead of AI"
    )
    args = parser.parse_args()

    analyze_logs(log_file=args.file, use_ai=not args.no_ai)
