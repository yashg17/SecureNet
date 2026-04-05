import os
import re
import time
import json
import datetime
from collections import defaultdict
from pathlib import Path
from dotenv import load_dotenv
from prometheus_client import Counter, Gauge, start_http_server

load_dotenv()

LOG_FILE_PATH = os.environ.get("LOG_FILE_PATH", "logs/app.log")
THRESHOLD = int(os.environ.get("FAILED_LOGIN_THRESHOLD", "5"))
WINDOW_SECONDS = int(os.environ.get("DETECTION_WINDOW_SECONDS", "60"))
METRICS_PORT = int(os.environ.get("METRICS_PORT", 8001))
REPORTS_DIR = Path("reports")

FAILED_LOGIN_RE = re.compile(r"FAILED_LOGIN \| ip=(?P<ip>[\d\.]+) \| username=(?P<username>\S+)")

brute_force_alerts_total = Counter("brute_force_alerts_total", "Brute-force alerts fired", ["ip"])
active_attackers_gauge = Gauge("active_brute_force_attackers", "Currently flagged IPs")
alert_failed_count = Gauge("brute_force_alert_failed_count", "Failed logins in last alert")

ip_times = defaultdict(list)
ip_samples = defaultdict(list)
ip_users = defaultdict(list)
alerted_ips = set()

def tail_file(path: str):
    p = Path(path)
    while not p.exists():
        time.sleep(1)
    with open(p, "r", encoding="utf-8") as f:
        f.seek(0, 2)
        last_size = f.tell()
        while True:
            if p.stat().st_size < last_size:
                f.seek(0)
            last_size = p.stat().st_size
            line = f.readline()
            if line:
                yield line.rstrip("\n")
            else:
                time.sleep(0.2)

def prune(now: float):
    cutoff = now - WINDOW_SECONDS
    for ip in list(ip_times.keys()):
        ip_times[ip] = [t for t in ip_times[ip] if t > cutoff]
        if not ip_times[ip]:
            ip_samples.pop(ip, None)
            ip_users.pop(ip, None)
            alerted_ips.discard(ip)

def trigger_pipeline(ip: str, count: int):
    from scripts.claude_triage import get_triage    
    import scripts.discord_alert as da

    triage = get_triage(
        attacking_ip=ip,
        failed_count=count,
        window_seconds=WINDOW_SECONDS,
        log_samples=ip_samples.get(ip, []),
        targeted_usernames=ip_users.get(ip, [])
    )                        

    da.send_alert(ip, count, WINDOW_SECONDS, triage)

    brute_force_alerts_total.labels(ip=ip).inc()
    alert_failed_count.set(count)
    active_attackers_gauge.set(sum(1 for t in ip_times.values() if t))

    REPORTS_DIR.mkdir(exist_ok=True)
    ts = datetime.datetime.utcnow().strftime("%D%m%y_%H%M%S")
    safe_ip = ip.replace(".", "_")
    path = REPORTS_DIR / f"alert_{safe_ip}_{ts}.json"
    path.write_text(json.dumps({
        "alert_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "attacking_ip": ip,
        "failed_count": count,
        'window_seconds': WINDOW_SECONDS,
        "triage": triage
    }, indent=2))
    print(f"[log_security] Report Saved To: {path}")

def process(line: str, now: float):
    m = FAILED_LOGIN_RE.search(line)
    if not m:
        return
    ip, username = m.group("ip"), m.group("username")
    ip_times[ip].append(now)
    ip_samples[ip].append(line)
    ip_users[ip].append(username)
    recent = [t for t in ip_times[ip] if t > now - WINDOW_SECONDS]
    print(f"[log_security] ip={ip} failures={len(recent)}/{THRESHOLD}")
    if len(recent) >= THRESHOLD and ip not in alerted_ips:
        alerted_ips.add(ip)
        trigger_pipeline(ip, len(recent))

def main():
    start_http_server(METRICS_PORT)
    print(f"[log_security] Watching {LOG_FILE_PATH} | threshold={THRESHOLD}/{WINDOW_SECONDS}s")
    last_prune = time.time()
    for line in tail_file(LOG_FILE_PATH):
        now = time.time()
        if now - last_prune > 30:
            prune(now)
            last_prune = now
        process(line, now)

if __name__ == "__main__":
    main()                        

