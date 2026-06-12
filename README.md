# Accelerant HubSpot → Slack Notifier

One universal webhook to send all your notifications to Slack.

## 🚀 Deploy for Free

### Option 1: [Render](https://render.com) (recommended ✅)

1. Fork/clone this repo to your GitHub
2. Go to **[render.com](https://dashboard.render.com) → New + → Web Service**
3. Connect your repo, branch `jimcred-repo`
4. Fill in:
   - **Name:** `hubspot-slack-notifier`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn notifier.main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** **Free** ($0/mo)
5. Add **Environment Variables**:
   - `SLACK_WEBHOOK_URL` → your Slack webhook URL
   - `HUBSPOT_PORTAL_ID` → `22606445`
   - `HUBSPOT_ACCESS_TOKEN` → your HubSpot PAT
6. Click **Deploy**
7. After deploy, your URL will be `https://hubspot-slack-notifier.onrender.com`

### Option 2: [Vercel](https://vercel.com) (serverless)

1. Push to your GitHub repo
2. Go to **[vercel.com](https://vercel.com) → Add New → Project**
3. Import your repo, branch `jimcred-repo`
4. **Framework Preset:** `Other`
5. **Build Command:** `pip install -r requirements.txt`
6. **Output Directory:** (leave blank)
7. Add env vars (same as above)
8. Deploy

> ⚠️ Vercel free tier has a **10-second timeout** — the `/trigger` endpoint may time out if HubSpot is slow.

## ⏰ Free Cron Jobs (every 30 min)

Use **[cron-job.org](https://cron-job.org)** (free, no account needed to start):

1. Go to cron-job.org → **Create Cronjob**
2. **URL:** `https://your-app.onrender.com/trigger`
3. **Method:** `POST`
4. **Schedule:** Every 30 minutes
5. Add a second cron job pinging `https://your-app.onrender.com/health` every **5 minutes** to keep Render's free tier awake.

## 📡 Endpoints

| Endpoint | Method | What it does |
|---|---|---|
| `/notify` | POST | Send any notification to Slack |
| `/trigger` | POST | Check HubSpot → notify Slack |
| `/health` | GET | Health check |

### Example: Send a notification

```bash
curl -X POST https://your-app.onrender.com/notify \
  -H "Content-Type: application/json" \
  -d '{"title":"🚀 Deployed","message":"v2.3.1 is live","event_type":"deploy"}'
```

### Example: Trigger HubSpot check

```bash
curl -X POST "https://your-app.onrender.com/trigger?hours=48"
```

## 📁 Project Structure

```
├── api/hubspot-activity.py     # Original Vercel serverless
├── notifier/
│   ├── main.py                 # FastAPI app (3 endpoints)
│   ├── slack.py                # Slack message sender
│   └── hubspot_checker.py      # HubSpot API client
├── requirements.txt
├── runtime.txt
├── .env.example
└── vercel.json
```
