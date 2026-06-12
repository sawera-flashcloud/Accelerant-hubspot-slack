"""Slack notification sender."""
import os
import httpx
from typing import Optional

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
HUBSPOT_PORTAL_ID = os.getenv("HUBSPOT_PORTAL_ID", "22606445")


def send(title: str, message: str, event_type: str = "notification", url: Optional[str] = None, fields: Optional[list] = None) -> bool:
    """Send a notification to Slack. Returns True on success."""
    if not SLACK_WEBHOOK_URL:
        raise RuntimeError("SLACK_WEBHOOK_URL not set")

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": title}}
    ]

    if fields:
        blocks.append({"type": "section", "fields": fields})
    else:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": message}})

    if url:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"<{url}|Open in HubSpot>"}
        })

    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"📬 {event_type}"}]
    })

    payload = {"text": f"{title}: {message}", "blocks": blocks}

    resp = httpx.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
    resp.raise_for_status()
    return True
