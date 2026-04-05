import os
import logging
import datetime
import time
from pathlib import Path
from flask import Flask, request, jsonify
from prometheus_client import start_http_server, Counter, Gauge
from dotenv import load_dotenv 

load_dotenv()

LOG_FILE_PATH = os.environ.get("LOG_FILE_PATH", "logs/app.log")
Path(LOG_FILE_PATH).parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%D-%m-%yT%H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Prometheus Metrics

login_attempts_total = Counter(
    "login_attempts_total",
    "Total login attempts",
    ["result"]
)
failed_login_last_seen = Gauge(
    "failed_login_last_seen_timestamp",
    "Last failed login timestamp per IP",
    ["ip address"]
)

app = Flask(__name__)

USERS = {
    "admin": "correct-password",
    "Yash": "securepass123"
}

@app.route("/login", methods=["POST"])
def login():
    ip = request.remote_addr
    username = request.form.get("username","")
    password = request.form.get("password","")
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"

    if USERS.get(username) == password:
        login_attempts_total.labels(result="success").inc()
        logger.info(f"SUCCESS_LOGIN | ip={ip} | username={username} | timestamp={timestamp}")
        return jsonify({"status": "ok"})
    
    login_attempts_total.labels(result="failed").inc()
    failed_login_last_seen.labels(ip_address=ip).set(time.time())
    logger.warning(f"FAILED_LOGIN| ip={ip} | username={username} | timestamp={timestamp}")
    return jsonify({"status": "failed"}), 401

@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200

@app.route("/")
def home():
    return jsonify({"message": "SecureNet Parent Portal"})

if __name__ == "__main__":
    metrics_port = int(os.environ.get("METRICS_PORT", 8000))
    start_http_server(metrics_port)
    logger.info(f"Metrics at http://0.0.0.0:{metrics_port}/metrics")
    app.run(host="0.0.0.0", port=int(os.environ.get("FLASK_PORT", 5000)), debug=False)
    
