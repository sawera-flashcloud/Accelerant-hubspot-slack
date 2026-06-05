---
name: slack-message-sender
description: Sends formatted HubSpot activity notifications to a chosen Slack channel using a Slack incoming webhook.
metadata:
  openclaw:
    requires:
      env: [SLACK_WEBHOOK_URL]
    primaryEnv: SLACK_WEBHOOK_URL
---

Use this skill when HubSpot activity should be posted to Slack.

**Slack destination:**
- Determined by `SLACK_WEBHOOK_URL`
- One webhook URL = one channel; create a new webhook per channel if needed

**Message layout:**
- **Header:** HubSpot Activity
- **Fields:** Activity, Object ID, Subscription, Property, New value, Source, Occurred at
- **Link:** "Open HubSpot record" — links into the HubSpot object view
- Empty fields are omitted automatically

**Rules:**
- Do not store messages anywhere.
- Do not create database or audit logs.
- Do not expose tokens or webhook URLs in messages.
- Slack channel history is the final record.
