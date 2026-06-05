---
name: hubspot-activity-fetcher
description: Receives HubSpot webhook activity events and extracts the useful activity fields for Slack notifications.
---

Use this skill when HubSpot activity-feed events, CRM object changes, contact updates, company updates, or deal updates need to be sent to Slack.

**Input:** HubSpot webhook payload (subscription object)

**Extracted fields:**
- `subscriptionType` — e.g. `deal.propertyChange`
- `objectId` — record ID in HubSpot
- `propertyName` — which field changed
- `propertyValue` — the new value
- `changeSource` — where the change happened (CRM_UI, API, etc.)
- `sourceId` — who made the change
- `occurredAt` — timestamp (epoch ms)

**Activity detection rules:**
| Pattern | Activity label |
|---|---|
| `contact.creation` | New contact created |
| `contact.propertyChange` | Contact updated |
| `company.creation` | New company created |
| `company.propertyChange` | Company updated |
| `deal.creation` | New deal created |
| `deal.propertyChange` | Deal updated |
| `deal.propertyChange` + `propertyName=dealstage` | Deal stage changed |
| `propertyName=lifecyclestage` | Lifecycle stage changed |
| `propertyName=hubspot_owner_id` | Owner changed |

**Rules:**
- Do not store anything in a database.
- Do not create HubSpot tasks or update records.
- Only extract data needed for Slack.
- If fields are missing, still return a simple activity summary.
