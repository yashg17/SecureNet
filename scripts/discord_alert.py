import os
import json
import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

SEVERITY_COLORS = {
    "CRITICAL": 15158332,
    "HIGH": 15105570,
    "MEDIUM": 16776960,
    "LOW": 3066993
}

DEFAULT_COLOR = 9807270

def send_alert(
        attacking_ip: str,
        failed_count: int,
        window_seconds: int,
        triage: dict
) -> bool:
    """
    Post a Discord embed with the brite-force alert and Claude's triage summary.
    
    """
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("[discord_alert] ERROR: DISCORD_WEBHOOK_URL is not set in .env — skipping")
        return False
    
    Severity = triage.get("Severity", "HIGH").upper()
    Attack_Type = triage.get("Attack_Type", "Brute-force login attack")
    Summary =  triage.get("Plain_English_Summary", "A Brute-Force attack was detected")
    Recommendation = triage.get("Recommendation", "Review logs and consider blocking the IP.")
    Targated = triage.get("Targated_Accounts", [])
    Urgency = triage.get("Urgency", "Review Soon")
    Confidence = triage.get("Confidence", "UNKNOWN")
    Auto_Block = triage.get("Auto_Block_Recommended", False)
    Attack_Confirmed = triage.get("Attack_Confirmed", True)

    Color = SEVERITY_COLORS.get(Severity, DEFAULT_COLOR)
    Timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    Targated_Str = ", ".join(Targated) if Targated else "UNKNOWN"
    Auto_Block_Str = "YES - Lambda block triggered" if Auto_Block else "NO - manual action required"

    embed = {
        "Title": f"SECURITY ALERT - {Attack_Type}",
        "Description": Summary,
        "Color": Color,
        "Timestamp": Timestamp,
        "Fields": [
            {"name": "Attacking IP", "value": f"`{attacking_ip}`", "inline": True},
            {"name": "Failed Attempts", "value": f"`{failed_count}` in `{window_seconds}s`", "inline": True},
            {"name": "Severity", "value": f"`{Severity}`", "inline": True},
            {"name": "Attack Confirmed", "value": f"`{'YES' if Attack_Confirmed else 'NO'}`", "inline": True},
            {"name": "AI Confidence", "value": f"`{Confidence}`", "inline": True},
            {"name": "Urgency", "value": Urgency, "inline": True},
            {"name": "Targeted Accounts", "value": Targated_Str, "inline": False},
            {"name": "Recommended Action", "value": Recommendation, "inline": False},
            {"name": "Auto IP Block", "value": Auto_Block_Str, "inline": False},
            {"name": "Grafana Dashboard", "value": "Open **SecureNet — Parent Portal Security** to see the spike", "inline": False}
        ],
        "footer": {"Text": "SecureNet AI Security Monitor | Claude Sonnet | log_security.py"}
    }

    payload = {
        "username": "SecureNet Security Bot",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/2716/2716652.png",
        "embeds": [embed]
    }

    print(f"[discord_alert] Posting alert to Discord - IP: {attacking_ip} | Severity: {Severity} ")

    try:
        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code in (200, 204):
            print(f"[discord_alert] Alert send Successfully (HTTP {response.status_code})")
            return True
        
        print(f"[discord_alert] Discord rejected the request - HTTP {response.status_code}")
        return False
    
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
        print(f"[discord_alert] ERROR: Discord request failed: {e}")
        return False
    
def send_pipeline_summary(build_number: str, findings_summary: dict) -> bool:
    """"
    Post a CI/CD pipeline security summary to Discord after a Jenkins build.
    """

    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("[discord_alert] ERROR: DISCORD_WEBHOOK_URL is not set in .env — skipping")
        return False
    
    Overall_Risk = findings_summary.get("Overall_Risk", "UNKNOWN").upper()
    Total = findings_summary.get("Total_Findings", 0)
    Critical_Count = findings_summary.get("Critical", 0)
    High_Count = findings_summary.get("High", 0)
    Summary_Text =  findings_summary.get("Executive_Summary", "No summary available.")
    Timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    Color = SEVERITY_COLORS.get(Overall_Risk, DEFAULT_COLOR)

    Pipeline_Status = "BLOCKED - fix before deploy" if Critical_Count > 0 else "PASSED - deploy proceeding"

    embed = {
        "Title": f"Pipeline Security Report - Build #{build_number}",
        "Description": "Summary_Text",
        "Color": Color,
        "Timestamp": Timestamp,
        "Fields": [
            {"name": "Pipeline Status", "value": f"`{Pipeline_Status}`", "inline": False},
            {"name": "Overall Risk", "value": f"`{Overall_Risk}`", "inline": True},
            {"name": "Total Findings", "value": f"`{Total}`", "inline": True},
            {"name": "CRITICAL", "value": f"`{Critical_Count}`", "inline": True},
            {"name": "HIGH", "value": f"`{High_Count}`", "inline": True}
        ],
        "footer": {"Text": "SecureNet CI/CD | SonarQube + Claude AI | Jenkins"}
    }

    payload = {"username": "SecureNet Pipeline Bot", "embeds": [embed]}

    try:
        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        return response.status_code in (200, 204)
    except requests.exceptions.RequestException as e:
        print(f"[discord_alert] ERROR sending pipeline summary : {e}")
        return False