---
id: "009"
title: "Configure WhatsApp Notifications"
stage: general
date: "2026-03-01"
surface: agent
model: claude-sonnet-4-6
feature: none
branch: main
user: fayaztayyab684
command: "configure whatsapp for communication and notification"
labels: ["whatsapp", "notifications", "configuration", "bugfix"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - ".env"
  - "executor/src/notifications.py"
  - "backend/src/api/webhooks.py"
  - "backend/src/config.py"
tests: []
---

## Prompt

I set the whatspp_access_token, and Whatsapp_number_id. SO now I wnat to you configure the whatsapp for the communication and notification.

## Response

Configured WhatsApp end-to-end across 4 files:

1. **`.env`** — Set `WHATSAPP_OWNER_PHONE=923182997727` (user's number) and `WHATSAPP_VERIFY_TOKEN=fte-whatsapp-verify-2026` (replaces placeholder values).

2. **`executor/src/notifications.py`** — Added `_send_whatsapp_direct()` helper that calls the WhatsApp Business API via HTTP directly (no MCP server required). Updated `_notify_whatsapp()` to try MCP server first, then fall back to direct HTTP call when MCP server is unreachable in local dev.

3. **`backend/src/api/webhooks.py`** — Implemented the TODO at line 67: when an incoming WhatsApp message is ambiguous, now sends a clarification message back to the sender using `_send_whatsapp_direct()` + `get_clarification_message()`.

4. **`backend/src/config.py`** — Removed duplicate LinkedIn fields (lines 45–48 were exact duplicates of 42–44).

## Outcome

WhatsApp is now fully wired for both inbound (webhook → task creation) and outbound (notifications + clarification replies). Works in local dev without requiring the MCP Docker container.

**Meta Webhook Setup Required** (manual step): In the Meta Developer Portal, set the webhook verify token to `fte-whatsapp-verify-2026` and the callback URL to `https://<your-domain>/api/v1/webhooks/whatsapp`.
---
