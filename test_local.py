#!/usr/bin/env python3
"""Test the HubSpot→Slack webhook locally."""
import os
import sys
import json
import time
import threading
import urllib.request
from http.server import HTTPServer

# Load .env
from pathlib import Path
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)

# Import the handler
sys.path.insert(0, str(Path(__file__).parent))
from api.hubspot_activity import handler

def run_server():
    server = HTTPServer(("0.0.0.0", 8888), handler)
    print("🚀 Server running on http://0.0.0.0:8888")
    server.serve_forever()

t = threading.Thread(target=run_server, daemon=True)
t.start()
time.sleep(1)

# ---- Test 1: GET healthcheck ----
print("\n─── Test 1: GET /api/hubspot-activity ───")
req = urllib.request.Request("http://localhost:8888/api/hubspot-activity")
resp = urllib.request.urlopen(req)
print(f"Status: {resp.status}")
print(f"Response: {resp.read().decode()}")

# ---- Test 2: POST a new deal created event ----
print("\n─── Test 2: POST – New deal created ───")
test_event = [{
    "objectId": 123456789,
    "subscriptionType": "deal.creation",
    "propertyName": "",
    "propertyValue": "New deal created",
    "changeSource": "API",
    "sourceId": "test-integration",
    "occurredAt": "2026-06-12T09:46:00Z"
}]
data = json.dumps(test_event).encode()
req = urllib.request.Request("http://localhost:8888/api/hubspot-activity", data=data, method="POST")
req.add_header("Content-Type", "application/json")
try:
    resp = urllib.request.urlopen(req)
    print(f"Status: {resp.status}")
    print(f"Response: {resp.read().decode()}")
except urllib.error.HTTPError as e:
    print(f"Status: {e.code}")
    print(f"Error: {e.read().decode()}")

# ---- Test 3: POST a deal stage change ----
print("\n─── Test 3: POST – Deal stage changed ───")
test_event2 = [{
    "objectId": 123456789,
    "subscriptionType": "deal.propertyChange",
    "propertyName": "dealstage",
    "propertyValue": "closedwon",
    "changeSource": "CRM_UI",
    "sourceId": "user@example.com",
    "occurredAt": "2026-06-12T09:50:00Z"
}]
data2 = json.dumps(test_event2).encode()
req2 = urllib.request.Request("http://localhost:8888/api/hubspot-activity", data=data2, method="POST")
req2.add_header("Content-Type", "application/json")
try:
    resp2 = urllib.request.urlopen(req2)
    print(f"Status: {resp2.status}")
    print(f"Response: {resp2.read().decode()}")
except urllib.error.HTTPError as e:
    print(f"Status: {e.code}")
    print(f"Error: {e.read().decode()}")

# ---- Test 4: POST a new contact created event ----
print("\n─── Test 4: POST – New contact created ───")
test_event3 = [{
    "objectId": 987654321,
    "subscriptionType": "contact.creation",
    "propertyName": "email",
    "propertyValue": "test@example.com",
    "changeSource": "IMPORT",
    "occurredAt": "2026-06-12T09:55:00Z"
}]
data3 = json.dumps(test_event3).encode()
req3 = urllib.request.Request("http://localhost:8888/api/hubspot-activity", data=data3, method="POST")
req3.add_header("Content-Type", "application/json")
try:
    resp3 = urllib.request.urlopen(req3)
    print(f"Status: {resp3.status}")
    print(f"Response: {resp3.read().decode()}")
except urllib.error.HTTPError as e:
    print(f"Status: {e.code}")
    print(f"Error: {e.read().decode()}")

print("\n✅ All tests completed. Check Slack for the messages!")
