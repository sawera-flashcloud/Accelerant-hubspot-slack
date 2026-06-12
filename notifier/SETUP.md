# Universal Notifier — Setup Guide

## Quick Start

```bash
# Install deps
pip install fastapi uvicorn httpx python-dotenv

# Copy and edit env vars
cp .env.example .env
# Fill in your SLACK_WEBHOOK_URL, HUBSPOT_PORTAL_ID, HUBSPOT_ACCESS_TOKEN

# Run
uvicorn notifier.main:app --host 0.0.0.0 --port 8000
```

## Endpoints

- `POST /notify`  — Send any notification payload to Slack
- `POST /trigger` — Check HubSpot for recent activity and notify Slack
- `GET /health`   — Health check

## Systemd Service

```bash
cp services/universal-notifier.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now universal-notifier
```

## Cron (every 30 min)

```bash
cp services/hubspot-cron /etc/cron.d/universal-notifier
```
