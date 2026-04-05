# SecureNet — Zero-Trust Parent Portal

AI-driven DevSecOps platform combining network security, automated pipelines,
Kubernetes zero-trust, Claude AI threat response, and Prometheus/Grafana observability.

---

## Architecture
```
GitHub Push → Jenkins Pipeline → Checkov + SonarQube + Claude → ECR → Terraform → EKS
                                                                              ↓
Brute-force attack → log_security.py → Claude API → Discord + Lambda IP Block
                                             ↓
                                    Prometheus (EC2) → Grafana (local)
```

---

## Where everything runs

| Component | Where |
|---|---|
| Flask app, scripts, Jenkins, SonarQube, Docker, K8s, Grafana | Local machine |
| Prometheus + Alertmanager | EC2 t3.small |
| EKS cluster, VPC, WAF, ECR, Lambda | AWS |
| All project files | VS Code + Git |

---

## Prerequisites

- Python 3.9+
- Docker installed and running
- kubectl configured
- Jenkins running locally on port 8080
- SonarQube running locally on port 9000
- Grafana running locally on port 3000
- EC2 t3.small with Prometheus and Alertmanager installed
- Anthropic API key
- Discord webhook URL
- AWS CLI configured

---

## Initial setup
```bash
git clone https://github.com/your-username/securenet.git
cd securenet
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys
```

---

## Jenkins configuration

### Credentials to add
Go to Jenkins → Manage Jenkins → Credentials → Global → Add:

| ID | Kind | Value |
|---|---|---|
| `ANTHROPIC_API_KEY` | Secret text | Your Claude API key |
| `SONAR_TOKEN` | Secret text | Your SonarQube token |
| `DISCORD_WEBHOOK_URL` | Secret text | Your Discord webhook URL |
| `AWS_ACCOUNT_ID` | Secret text | Your AWS account ID |
| `dockerhub-creds` | Username/password | DockerHub credentials |

### SonarQube server
Jenkins → Manage Jenkins → Configure System → SonarQube servers:
- Name: `SonarQube`
- URL: `http://localhost:9000`
- Token: add credential → secret text → paste SonarQube token

### SonarQube scanner tool
Jenkins → Manage Jenkins → Global Tool Configuration → SonarQube Scanner:
- Name: `Sonar Scanner`
- Install automatically: checked

---

## Webhook URLs

| Service | Where to configure | URL to enter |
|---|---|---|
| GitHub webhook | Repo → Settings → Webhooks | `http://YOUR_JENKINS_IP:8080/github-webhook/` |
| SonarQube webhook | SonarQube → Admin → Webhooks | `http://YOUR_JENKINS_IP:8080/sonarqube-webhook/` |

---

## Running the detection system
```bash
# Terminal 1 — Flask app
python app/app.py

# Terminal 2 — log watcher
python scripts/log_security.py

# Simulate brute-force attack
for i in $(seq 1 10); do
  curl -s -X POST http://localhost:5000/login \
    -d "username=admin&password=wrong$i"
  sleep 0.5
done
```

---

## Prometheus on EC2

After installing (see docs/GRAFANA_SETUP.md), Prometheus is available at:
`http://YOUR_EC2_IP:9090`

Alertmanager: `http://YOUR_EC2_IP:9093`

---

## Grafana dashboard

Import the **SecureNet — Parent Portal Security** dashboard.
Prometheus data source: `http://YOUR_EC2_IP:9090`

See `docs/GRAFANA_SETUP.md` for full panel configuration.
