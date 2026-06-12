"""Check HubSpot for recent activity and send notifications."""
import os
import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional

from . import slack

HUBSPOT_TOKEN = os.getenv("HUBSPOT_ACCESS_TOKEN")
HUBSPOT_BASE = "https://api.hubapi.com"

# Cache for owner IDs → names
_owner_cache: dict[str, str] = {}


async def _resolve_owner_name(owner_id: str) -> str:
    """Look up an owner ID and return their name. Results are cached."""
    if not owner_id:
        return "Unassigned"
    if owner_id in _owner_cache:
        return _owner_cache[owner_id]
    headers = {"Authorization": f"Bearer {HUBSPOT_TOKEN}"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{HUBSPOT_BASE}/crm/v3/owners/{owner_id}", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                first = data.get("firstName", "")
                last = data.get("lastName", "")
                name = f"{first} {last}".strip() or owner_id
                _owner_cache[owner_id] = name
                return name
    except Exception:
        pass
    _owner_cache[owner_id] = owner_id
    return owner_id


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
    owner_raw = props.get("hubspot_owner_id", "")
    owner = _owner_cache.get(owner_raw, owner_raw) if owner_raw else "Unassigned"

    title = f"💼 Deal: {name}"
    message = f"${amount} | Stage: {stage} | Owner: {owner}"
    fields = [
        {"type": "mrkdwn", "text": f"*Deal:* {name}"},
        {"type": "mrkdwn", "text": f"*Amount:* ${amount}"},
        {"type": "mrkdwn", "text": f"*Stage:* {stage}"},
        {"type": "mrkdwn", "text": f"*Owner:* {owner}"},
    ]
    url = f""
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
    url = f""
    return title, message, fields, url


async def _load_owners() -> None:
    """Pre-load all HubSpot owners into the cache."""
    if _owner_cache:
        return  # already loaded
    headers = {"Authorization": f"Bearer {HUBSPOT_TOKEN}"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{HUBSPOT_BASE}/crm/v3/owners", headers=headers)
            if resp.status_code == 200:
                for owner in resp.json().get("results", []):
                    oid = owner.get("id")
                    first = owner.get("firstName", "")
                    last = owner.get("lastName", "")
                    if oid:
                        _owner_cache[str(oid)] = f"{first} {last}".strip() or str(oid)
    except Exception:
        pass


async def check_and_notify(hours: int = 24) -> dict:
    """Check HubSpot for recent activity and send Slack notifications."""
    results = {"deals_sent": 0, "contacts_sent": 0, "errors": []}

    # Pre-load owner names so Slack shows real names, not IDs
    await _load_owners()

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
