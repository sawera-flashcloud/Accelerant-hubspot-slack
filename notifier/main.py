"""FastAPI universal notification webhook.
POST /notify  — Send any notification payload to Slack
POST /trigger — Check HubSpot for recent activity and notify Slack
GET  /health  — Health check
"""
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from . import slack
from .hubspot_checker import check_and_notify

app = FastAPI(
    title="Universal Notifier",
    description="One webhook to send all your notifications to Slack",
    version="1.0.0"
)


# ─── Models ───────────────────────────────────────────────────

class NotifyRequest(BaseModel):
    title: str = Field(default="Notification", description="Title / header")
    message: str = Field(..., description="Body text")
    type: str = Field(default="notification", alias="event_type")
    url: Optional[str] = Field(default=None, description="Optional link URL")
    fields: Optional[list[dict]] = Field(default=None, description="Optional Slack section fields")


class NotifyResponse(BaseModel):
    ok: bool
    sent_to_slack: bool


class TriggerResponse(BaseModel):
    ok: bool
    deals_sent: int
    contacts_sent: int
    errors: list[str]


# ─── Endpoints ────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"ok": True, "app": "universal-notifier"}


@app.post("/notify", response_model=NotifyResponse)
async def notify(req: NotifyRequest):
    """Universal notification endpoint.
    Send any payload and it gets forwarded to your Slack webhook.
    """
    try:
        slack.send(
            title=req.title,
            message=req.message,
            event_type=req.type,
            url=req.url,
            fields=req.fields
        )
        return NotifyResponse(ok=True, sent_to_slack=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/trigger", response_model=TriggerResponse)
async def trigger(hours: int = 24):
    """Check HubSpot for recent activity and send notifications to Slack.
    Use this endpoint in a cron job to get periodic updates.
    """
    try:
        result = await check_and_notify(hours=hours)
        return TriggerResponse(
            ok=len(result["errors"]) == 0,
            deals_sent=result["deals_sent"],
            contacts_sent=result["contacts_sent"],
            errors=result["errors"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── CLI entrypoint ──────────────────────────────────────────

def main():
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("notifier.main:app", host="0.0.0.0", port=port, reload=False)
