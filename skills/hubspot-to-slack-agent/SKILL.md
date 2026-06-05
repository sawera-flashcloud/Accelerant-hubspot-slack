---
name: hubspot-to-slack-agent
description: Simple automation agent that sends HubSpot activity-feed webhook events to one Slack channel.
---

Use this skill when the user wants HubSpot activity-feed notifications sent to Slack.

**Workflow:**
1. Receive HubSpot webhook event (POST to `/api/hubspot-activity`)
2. Use `hubspot-activity-fetcher` to extract useful fields
3. Use `slack-message-sender` to post the activity into Slack
4. Return a success response

**Expected response:**
```json
{ "ok": true, "sent_to_slack": 1 }
```

**Rules:**
- No database. No SQLite. No Supabase.
- No HubSpot task creation or record updates.
- No audit logs.
- Slack chat history is the permanent record.
- Only send activity notifications to the configured Slack channel.
