# SecureNet Architecture

## Layer 1 — Networking (Terraform)
Multi-AZ VPC, ALB in public subnet, App+DB in private subnets.
WAF blocks SQLi/XSS. Shield Standard protects ALB. VPC Flow Logs go to CloudWatch.

## Layer 2 — Pipeline (Jenkins)
GitHub push → Checkov (IaC) → SonarQube SAST → Quality Gate
→ Claude summary → Docker push ECR → Terraform apply → EKS deploy

## Layer 3 — Kubernetes (EKS)
Namespaces: frontend, backend, database.
Network Policies enforce zero-trust between namespaces.
Istio mTLS encrypts pod-to-pod traffic. Falco detects runtime threats.
RBAC gives each service account minimum permissions.

## Layer 4 — AI Brain (Claude API)
log_security.py tails logs. On threshold breach:
Claude triages → Discord alert → Lambda blocks attacking IP in Security Group.

## Layer 5 — Observability
Prometheus HA on EC2 scrapes all targets every 15s.
Alertmanager routes critical alerts to Discord.
Grafana on local machine shows security dashboard with template variables.
