"""Check HubSpot for recent activity and send notifications — with dedup."""
import os
import json
import httpx
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import slack

HUBSPOT_TOKEN = os.getenv("HUBSPOT_ACCESS_TOKEN")
HUBSPOT_BASE = "https://api.hubapi.com"

# Cache for owner IDs → names
_owner_cache: dict[str, str] = {}

# State file path for dedup (stores last-seen timestamps)
_STATE_FILE = Path(__file__).parent / ".dedup_state.json"


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text())
        except Exception:
            pass
    return {"last_deal_time": None, "last_contact_time": None}


def _save_state(state: dict) -> None:
    _STATE_FILE.write_text(json.dumps(state, indent=2))


def _get_since(state_key: str, fallback_hours: int = 48) -> str:
    """Return the ISO timestamp to filter by — either last seen or fallback window."""
    state = _load_state()
    last = state.get(state_key)
    if last:
        return last
    return (datetime.now(timezone.utc) - timedelta(hours=fallback_hours)).isoformat()


def _update_latest(state_key: str, items: list[dict], prop: str = "hs_lastmodifieddate") -> None:
    """Update the dedup state with the newest timestamp from fetched items."""
    if not items:
        return
    timestamps = []
    for item in items:
        val = item.get("properties", {}).get(prop)
        if val:
            timestamps.append(val)
    if timestamps:
        timestamps.sort(reverse=True)
        state = _load_state()
        # Add 1 second so we don't re-fetch the same record
        state[state_key] = timestamps[0]
        _save_state(state)


async def _load_owners() -> None:
    """Pre-load all HubSpot owners into the cache."""
    if _owner_cache:
        return
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


def _search_body(prop: str, since: str, extra_props: list, limit: int = 100) -> dict:
    return {
        "limit": limit,
        "filterGroups": [{
            "filters": [{
                "propertyName": prop,
                "operator": "GT",
                "value": since
            }]
        }],
        "properties": extra_props + [prop, "createdate"],
        "sorts": [{"propertyName": prop, "direction": "DESCENDING"}]
    }


async def _fetch_objects(obj_type: str, body: dict) -> list[dict]:
    """Generic HubSpot CRM search."""
    headers = {"Authorization": f"Bearer {HUBSPOT_TOKEN}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{HUBSPOT_BASE}/crm/v3/objects/{obj_type}/search",
            headers=headers,
            json=body
        )
        resp.raise_for_status()
        return resp.json().get("results", [])


# ─── Deal helpers ─────────────────────────────────────────

DEAL_PROPS = ["dealname", "amount", "dealstage", "hubspot_owner_id"]


def build_deal_fields(deal: dict) -> tuple[str, str, list, str]:
    props = deal.get("properties", {})
    name = props.get("dealname", "Untitled deal")
    amount = props.get("amount", "Not set")
    stage = props.get("dealstage", "Unknown")
    owner_raw = props.get("hubspot_owner_id", "")
    owner = _owner_cache.get(owner_raw, owner_raw) if owner_raw else "Unassigned"

    title = f"💼 Deal: {name}"
    fields = [
        {"type": "mrkdwn", "text": f"*Deal:* {name}"},
        {"type": "mrkdwn", "text": f"*Amount:* ${amount}"},
        {"type": "mrkdwn", "text": f"*Stage:* {stage}"},
        {"type": "mrkdwn", "text": f"*Owner:* {owner}"},
    ]
    return title, f"${amount} | Stage: {stage}", fields, ""


# ─── Contact helpers ──────────────────────────────────────

CONTACT_PROPS = ["firstname", "lastname", "email", "hs_lead_status"]


def build_contact_fields(contact: dict) -> tuple[str, str, list, str]:
    props = contact.get("properties", {})
    first = props.get("firstname", "")
    last = props.get("lastname", "")
    email = props.get("email", "No email")
    lead_status = props.get("hs_lead_status", "Unknown")
    name = f"{first} {last}".strip() or "Unnamed contact"

    title = f"👤 Contact: {name}"
    fields = [
        {"type": "mrkdwn", "text": f"*Name:* {name}"},
        {"type": "mrkdwn", "text": f"*Email:* {email}"},
        {"type": "mrkdwn", "text": f"*Lead Status:* {lead_status}"},
    ]
    return title, f"{email} | {lead_status}", fields, ""


# ─── Main check ───────────────────────────────────────────

async def check_and_notify(fallback_hours: int = 48) -> dict:
    """Check HubSpot for *new* activity (since last run) and send to Slack."""
    results = {"deals_sent": 0, "contacts_sent": 0, "errors": []}

    await _load_owners()

    # ── Deals ──
    try:
        since = _get_since("last_deal_time", fallback_hours)
        body = _search_body("hs_lastmodifieddate", since, DEAL_PROPS)
        deals = await _fetch_objects("deals", body)

        for deal in deals:
            title, msg, fields, url = build_deal_fields(deal)
            slack.send(title=title, message=msg, event_type="HubSpot Deal", url=url, fields=fields)
            results["deals_sent"] += 1

        _update_latest("last_deal_time", deals)
    except Exception as e:
        results["errors"].append(f"Deals error: {e}")

    # ── Contacts ──
    try:
        since = _get_since("last_contact_time", fallback_hours)
        body = _search_body("hs_lastmodifieddate", since, CONTACT_PROPS)
        contacts = await _fetch_objects("contacts", body)

        for contact in contacts:
            title, msg, fields, url = build_contact_fields(contact)
            slack.send(title=title, message=msg, event_type="HubSpot Contact", url=url, fields=fields)
            results["contacts_sent"] += 1

        _update_latest("last_contact_time", contacts)
    except Exception as e:
        results["errors"].append(f"Contacts error: {e}")

    return results
