"""
log_generator.py
-----------------
Simulates an application generating log entries.
Writes logs to logs/app.log file.
Run this to generate fresh log data for analysis.
"""

import random
import time
import os
from datetime import datetime

# ---- Configuration ----
LOG_FILE = os.path.join("logs", "app.log")      # Output log file
NUM_LOGS = 100                                    # How many log lines to generate
ANOMALY_BURST_CHANCE = 0.15                       # 15% chance of an error burst

# Different types of log messages
LOG_TEMPLATES = {
    "INFO": [
        "User login successful - user_id={}",
        "Page loaded - /dashboard - {}ms",
        "API request processed - /api/data - {}ms",
        "Database query completed - {}ms",
        "Health check passed - all systems normal",
        "User logout - user_id={}",
        "Backup completed successfully",
        "Cache refreshed successfully",
    ],
    "WARNING": [
        "High memory usage detected - {}%",
        "Response time high - {}ms",
        "Disk space below {}% - /dev/sda1",
        "Retry attempt {} for service connection",
        "Deprecated API endpoint accessed - /api/v1/legacy",
    ],
    "ERROR": [
        "Failed to connect to database - Connection timeout",
        "NullPointerException in module auth.py line {}",
        "Unauthorized access attempt - IP: 192.168.1.{}",
        "Service unavailable - payment_service down",
        "Stack overflow detected - process crash imminent",
        "File not found: /var/data/config.json",
    ]
}

def generate_log_line(level):
    """Creates a single log line with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    template = random.choice(LOG_TEMPLATES[level])

    # Fill in random numbers in the template
    message = template.format(
        random.randint(100, 999),
        random.randint(50, 3000),
        random.randint(1, 99),
    )
    return f"{timestamp} {level} {message}"

def generate_logs():
    """Main function to generate and write logs."""
    os.makedirs("logs", exist_ok=True)  # Create logs folder if not exists

    print(f"[*] Generating {NUM_LOGS} log entries → {LOG_FILE}")

    with open(LOG_FILE, "w") as f:
        for i in range(NUM_LOGS):
            # Mostly INFO logs (normal behavior)
            # Occasionally trigger error bursts (anomaly)
            if random.random() < ANOMALY_BURST_CHANCE:
                # Error burst: write 4-6 ERROR lines in a row
                burst_size = random.randint(4, 6)
                print(f"  ⚠ Anomaly burst at line {i} ({burst_size} errors)")
                for _ in range(burst_size):
                    line = generate_log_line("ERROR")
                    f.write(line + "\n")
                    print(f"    {line}")
                    time.sleep(0.01)
            else:
                # Normal log: 80% INFO, 20% WARNING
                level = "INFO" if random.random() < 0.80 else "WARNING"
                line = generate_log_line(level)
                f.write(line + "\n")

            time.sleep(0.02)  # Small delay to simulate real-time logging

    print(f"\n✅ Done! Log file created: {LOG_FILE}")
    print("   Run 'python analyzer.py' to analyze anomalies.\n")

if __name__ == "__main__":
    generate_logs()
