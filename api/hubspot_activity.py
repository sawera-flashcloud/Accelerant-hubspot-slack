import os
import json
import requests
from http.server import BaseHTTPRequestHandler


SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
HUBSPOT_PORTAL_ID = os.getenv("HUBSPOT_PORTAL_ID", "")


def detect_activity_type(event: dict) -> str:
    subscription_type = str(event.get("subscriptionType", "")).lower()
    property_name = str(event.get("propertyName", "")).lower()
    change_source = str(event.get("changeSource", "")).lower()

    text = f"{subscription_type} {property_name} {change_source}"

    if "deal" in text and "dealstage" in text:
        return "Deal stage changed"
    if "deal" in text and "created" in text:
        return "New deal created"
    if "deal" in text:
        return "Deal updated"
    if "contact" in text and "created" in text:
        return "New contact created"
    if "contact" in text:
        return "Contact updated"
    if "company" in text and "created" in text:
        return "New company created"
    if "company" in text:
        return "Company updated"
    if "lifecyclestage" in text:
        return "Lifecycle stage changed"
    if "hubspot_owner_id" in text:
        return "Owner changed"

    return "HubSpot activity"


def hubspot_object_url(event: dict) -> str:
    object_id = event.get("objectId")
    subscription_type = str(event.get("subscriptionType", "")).split(".")[0].lower()

    if not HUBSPOT_PORTAL_ID or not object_id:
        return ""

    base = f"https://app.hubspot.com/contacts/{HUBSPOT_PORTAL_ID}"

    if subscription_type == "contact":
        return f"{base}/contact/{object_id}"
    if subscription_type == "company":
        return f"{base}/company/{object_id}"
    if subscription_type == "deal":
        return f"{base}/deal/{object_id}"

    return base


def format_slack_message(event: dict) -> dict:
    activity_type = detect_activity_type(event)

    fields = []
    fields.append({"type": "mrkdwn", "text": f"*Activity:*\n{activity_type}"})
    fields.append({"type": "mrkdwn", "text": f"*Object ID:*\n{event.get('objectId', 'unknown')}"})
    fields.append({"type": "mrkdwn", "text": f"*Subscription:*\n{event.get('subscriptionType', 'unknown')}"})

    if event.get("propertyName"):
        fields.append({"type": "mrkdwn", "text": f"*Property:*\n{event['propertyName']}"})
    if event.get("propertyValue"):
        fields.append({"type": "mrkdwn", "text": f"*New value:*\n{event['propertyValue']}"})
    if event.get("changeSource"):
        fields.append({"type": "mrkdwn", "text": f"*Source:*\n{event['changeSource']}"})
    if event.get("sourceId"):
        fields.append({"type": "mrkdwn", "text": f"*Source ID:*\n{event['sourceId']}"})
    if event.get("occurredAt"):
        fields.append({"type": "mrkdwn", "text": f"*Occurred at:*\n{event['occurredAt']}"})

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "HubSpot Activity"}},
        {"type": "section", "fields": fields},
    ]

    record_url = hubspot_object_url(event)
    if record_url:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"<{record_url}|Open HubSpot record>"}
        })

    return {"text": f"HubSpot Activity: {activity_type}", "blocks": blocks}


def send_to_slack(message: dict) -> None:
    if not SLACK_WEBHOOK_URL:
        raise RuntimeError("Missing SLACK_WEBHOOK_URL environment variable")
    resp = requests.post(SLACK_WEBHOOK_URL, json=message, timeout=10)
    resp.raise_for_status()


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True, "message": "HubSpot to Slack endpoint is live"}).encode("utf-8"))

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode("utf-8"))
            events = payload if isinstance(payload, list) else [payload]

            sent = 0
            for event in events:
                msg = format_slack_message(event)
                send_to_slack(msg)
                sent += 1

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "sent_to_slack": sent}).encode("utf-8"))

        except Exception as error:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": str(error)}).encode("utf-8"))
