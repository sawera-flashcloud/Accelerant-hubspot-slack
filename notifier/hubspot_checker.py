"""Check HubSpot for recent activity and send notifications."""
import os
import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional

from . import slack

HUBSPOT_TOKEN = os.getenv("HUBSPOT_ACCESS_TOKEN")
HUBSPOT_BASE = "https://api.hubapi.com"


async def get_recent_deals(hours: int = 24, limit: int = 10) -> list[dict]:
    """Fetch recently created/modified deals from HubSpot."""
    if not HUBSPOT_TOKEN:
        raise RuntimeError("HUBSPOT_ACCESS_TOKEN not set")

    after = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    headers = {
        "Authorization": f"Bearer {HUBSPOT_TOKEN}",
        "Content-Type": "application/json"
    }

    body = {
        "limit": limit,
        "filterGroups": [{
            "filters": [{
                "propertyName": "hs_lastmodifieddate",
                "operator": "GTE",
                "value": after
            }]
        }],
        "properties": ["dealname", "amount", "dealstage", "hubspot_owner_id", "createdate"],
        "sorts": [{"propertyName": "hs_lastmodifieddate", "direction": "DESCENDING"}]
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{HUBSPOT_BASE}/crm/v3/objects/deals/search",
            headers=headers,
            json=body
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])


async def get_recent_contacts(hours: int = 24, limit: int = 10) -> list[dict]:
    """Fetch recently created/modified contacts."""
    if not HUBSPOT_TOKEN:
        raise RuntimeError("HUBSPOT_ACCESS_TOKEN not set")

    after = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    headers = {
        "Authorization": f"Bearer {HUBSPOT_TOKEN}",
        "Content-Type": "application/json"
    }

    body = {
        "limit": limit,
        "filterGroups": [{
            "filters": [{
                "propertyName": "hs_lastmodifieddate",
                "operator": "GTE",
                "value": after
            }]
        }],
        "properties": ["email", "firstname", "lastname", "createdate", "hs_lead_status"],
        "sorts": [{"propertyName": "hs_lastmodifieddate", "direction": "DESCENDING"}]
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{HUBSPOT_BASE}/crm/v3/objects/contacts/search",
            headers=headers,
            json=body
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])


def build_deal_fields(deal: dict) -> tuple[str, str, list, str]:
    """Extract Slack fields from a HubSpot deal."""
    props = deal.get("properties", {})
    deal_id = deal.get("id", "?")
    name = props.get("dealname", "Untitled deal")
    amount = props.get("amount", "Not set")
    stage = props.get("dealstage", "Unknown")
    owner = props.get("hubspot_owner_id", "Unassigned")

    title = f"💼 Deal: {name}"
    message = f"${amount} | Stage: {stage} | Owner: {owner}"
    fields = [
        {"type": "mrkdwn", "text": f"*Deal:* {name}"},
        {"type": "mrkdwn", "text": f"*Amount:* ${amount}"},
        {"type": "mrkdwn", "text": f"*Stage:* {stage}"},
        {"type": "mrkdwn", "text": f"*Owner:* {owner}"},
    ]
    url = f"https://app.hubspot.com/contacts/{slack.HUBSPOT_PORTAL_ID}/deal/{deal_id}"
    return title, message, fields, url


def build_contact_fields(contact: dict) -> tuple[str, str, list, str]:
    """Extract Slack fields from a HubSpot contact."""
    props = contact.get("properties", {})
    contact_id = contact.get("id", "?")
    first = props.get("firstname", "")
    last = props.get("lastname", "")
    email = props.get("email", "No email")
    lead_status = props.get("hs_lead_status", "Unknown")

    name = f"{first} {last}".strip() or "Unnamed contact"
    title = f"👤 Contact: {name}"
    message = f"{email} | Status: {lead_status}"
    fields = [
        {"type": "mrkdwn", "text": f"*Name:* {name}"},
        {"type": "mrkdwn", "text": f"*Email:* {email}"},
        {"type": "mrkdwn", "text": f"*Lead Status:* {lead_status}"},
    ]
    url = f"https://app.hubspot.com/contacts/{slack.HUBSPOT_PORTAL_ID}/contact/{contact_id}"
    return title, message, fields, url


async def check_and_notify(hours: int = 24) -> dict:
    """Check HubSpot for recent activity and send Slack notifications."""
    results = {"deals_sent": 0, "contacts_sent": 0, "errors": []}

    # Check deals
    try:
        deals = await get_recent_deals(hours=hours)
        for deal in deals:
            title, msg, fields, url = build_deal_fields(deal)
            slack.send(title=title, message=msg, event_type="HubSpot Deal", url=url, fields=fields)
            results["deals_sent"] += 1
    except Exception as e:
        results["errors"].append(f"Deals error: {e}")

    # Check contacts
    try:
        contacts = await get_recent_contacts(hours=hours)
        for contact in contacts:
            title, msg, fields, url = build_contact_fields(contact)
            slack.send(title=title, message=msg, event_type="HubSpot Contact", url=url, fields=fields)
            results["contacts_sent"] += 1
    except Exception as e:
        results["errors"].append(f"Contacts error: {e}")

    return results
