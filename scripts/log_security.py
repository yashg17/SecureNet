import os
import re
import time
import json
import datetime
import sys
from collections import defaultdict
from pathlib import Path
from prometheus_client import Counter, Gauge, start_http_server

# Add the project root to sys.path so it can find scripts.claude_triage
project_root = str(Path(__file__).resolve().parent.parent)
sys.path.append(project_root)

# --- CONFIGURATION ---
METRICS_PORT = 8000
LOG_FILE_PATH = "logs/app.log"
THRESHOLD = 5
WINDOW_SECONDS = 60
REPORTS_DIR = Path(project_root) / "reports"
LOG_PATH = Path(project_root) / LOG_FILE_PATH

# Ensure directories exist
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
if not LOG_PATH.exists():
    LOG_PATH.touch()
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Regex
FAILED_LOGIN_RE = re.compile(r"FAILED_LOGIN \| ip=(?P<ip>[\d\.]+) \| username=(?P<username>\S+)")

# --- METRICS ---
brute_force_alerts_total = Counter("brute_force_alerts_total", "Total alerts", ["ip"])
active_attackers_gauge = Gauge("active_brute_force_attackers", "Current attackers")
alert_failed_count = Gauge("brute_force_alert_failed_count", "Last alert count")

ip_times = defaultdict(list)
ip_samples = defaultdict(list)
ip_users = defaultdict(list)
alerted_ips = set()

def tail_file(path):
    with open(path, "r", encoding="utf-8") as f:
        f.seek(0, 2)
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.5)
                continue
            yield line.rstrip("\n")

def trigger_pipeline(ip, count):
    try:
        # Import inside function to avoid startup crashes
        from scripts.claude_triage import get_triage
        import scripts.discord_alert as da

        triage = get_triage(ip, count, WINDOW_SECONDS, ip_samples.get(ip, []), ip_users.get(ip, []))
        da.send_alert(ip, count, WINDOW_SECONDS, triage)
    except Exception as e:
        print(f"[Error] Pipeline failed: {e}")
        triage = "Triage failed."

    brute_force_alerts_total.labels(ip=ip).inc()
    alert_failed_count.set(count)

def process_line(line, now):
    match = FAILED_LOGIN_RE.search(line)
    if not match: return
    ip, user = match.group("ip"), match.group("username")
    ip_times[ip].append(now)
    ip_samples[ip].append(line)
    ip_users[ip].append(user)
    recent = [t for t in ip_times[ip] if t > now - WINDOW_SECONDS]
    if len(recent) >= THRESHOLD and ip not in alerted_ips:
        alerted_ips.add(ip)
        trigger_pipeline(ip, len(recent))

def main():
    try:
         start_http_server(METRICS_PORT, addr='0.0.0.0')
        print(f"[Online] Port {METRICS_PORT} | Log: {LOG_PATH}")
        for line in tail_file(LOG_PATH):
            process_line(line, time.time())
    except Exception as e:
        print(f"[Critical] {e}")

if __name__ == "__main__":
    main()
