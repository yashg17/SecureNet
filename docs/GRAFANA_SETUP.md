# Grafana Dashboard Setup Guide

## Data source
Grafana → Configuration → Data sources → Add → Prometheus
- Name: Prometheus
- URL: http://34.239.176.44:9090
- Save and test — should show "Data source is working"

## Dashboard
Name: SecureNet — Parent Portal Security

## Variables
Settings → Variables → New:
1. Name: instance | Type: Query | Query: label_values(login_attempts_total, instance)
2. Name: job      | Type: Query | Query: label_values(up, job)
3. Name: interval | Type: Interval | Values: 1m,5m,10m,30m,1h

## Row 1 — Security Overview
Panels: Failed Logins/min, Active Attackers, Total Alerts, Login Success Rate

## Row 2 — Attack Intelligence
Panels: Failed Logins by IP, Brute-Force Alert Rate, Last Alert Count

## Row 3 — System Health
Panels: Prometheus Scrape Success, Scrape Duration, Jenkins Up

## Full PromQL and panel settings
See README.md in the repo root for all PromQL queries and threshold values.
