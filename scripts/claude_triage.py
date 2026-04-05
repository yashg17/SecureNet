import os
import json
import boto3
import anthropic
from anthropic.types import TextBlock
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are a security operations analyst responding to live alerts.
You will receive evidence of a potential brute-force attack.
Return ONLY a JSON object — no markdown fences, no explanation:
{
  "Attack_Confirmed": true,
  "Attack_Type": "Brute-force login attack",
  "Severity": "HIGH",
  "Plain_English_Summary": "Max 3 sentences for a Discord embed.",
  "Targeted_Accounts": ["admin"],
  "Recommendation": "Max 3 sentences with specific actions.",
  "Urgency": "Respond within 5 minutes",
  "Confidence": "HIGH",
  "Auto_Block_Recommended": true
}
Severity: CRITICAL|HIGH|MEDIUM|LOW
Confidence: HIGH|MEDIUM|LOW """

def get_triage(attacking_ip: str, failed_count: int, window_seconds: int,
               log_samples: list, targeted_usernames: list) -> dict:
    
    api_key = os.environ.get("CLAUDE_API_KEY")
    if not api_key:
        return _fallback(attacking_ip, failed_count)

    client = anthropic.Anthropic(api_key=api_key)
    evidence = "\n".join(log_samples[:10])
    usernames = ", ".join(set(targeted_usernames)) or "unknown"

    user_msg = f"""Brute-force alert triage required.
Attacking IP: {attacking_ip}
Failed logins: {failed_count} in {window_seconds}s
Targeted usernames: {usernames}
Log evidence:
{evidence}"""

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6", # Updated to a valid model name
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}]
        )

        # FIX: Extract text only from TextBlock objects to satisfy Pylance
        raw_text = ""
        for block in msg.content:
            if isinstance(block, TextBlock):
                raw_text += block.text

        raw = raw_text.strip()

        # Handle potential markdown code fences if Claude includes them
        if raw.startswith("```"):
            lines = raw.splitlines()
            # Remove the first and last lines (the backticks)
            raw = "\n".join([line for line in lines if not line.strip().startswith("```")])

        triage = json.loads(raw.strip())

        # Auto-block via Lambda if Claude recommends it
        if triage.get("Auto_Block_Recommended") and triage.get("Attack_Confirmed"):
            _trigger_lambda_block(attacking_ip)

        return triage

    except Exception as e:
        print(f"[claude_triage] ERROR: {e}")
        return _fallback(attacking_ip, failed_count)

def _trigger_lambda_block(ip: str):
    """Invoke AWS Lambda to update the Security Group and block the IP."""
    fn_name = os.environ.get("LAMBDA_FUNCTION_NAME", "block-attacker-ip")
    region  = os.environ.get("AWS_REGION", "us-east-1")
    try:
        client = boto3.client("lambda", region_name=region)
        payload = json.dumps({"attacking_ip": ip, "action": "block"})
        resp = client.invoke(FunctionName=fn_name, Payload=payload.encode())
        print(f"[claude_triage] Lambda block triggered for {ip} — status: {resp['StatusCode']}")
    except Exception as e:
        print(f"[claude_triage] Lambda block failed for {ip}: {e}")

def _fallback(ip: str, count: int) -> dict:
    return {
        "Attack_Confirmed": True,
        "Attack_Type": "Brute-force login attack",
        "Severity": "HIGH",
        "Plain_English_Summary": f"IP {ip} made {count} failed login attempts. Claude API unavailable — manual review required.",
        "Targeted_Accounts": [],
        "Recommendation": "Block the IP at the firewall. Review logs manually.",
        "Urgency": "Respond within 15 minutes",
        "Confidence": "LOW",
        "Auto_Block_Recommended": False
    }
