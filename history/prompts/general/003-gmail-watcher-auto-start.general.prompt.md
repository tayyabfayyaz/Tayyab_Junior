---
id: "003"
title: "Gmail Watcher Auto Start on Backend"
stage: general
date: "2026-02-20"
surface: agent
model: claude-sonnet-4-6
feature: none
branch: 001-fte-task-executor
user: fayaztayyab684
command: "make gmail watcher run by default when the frontend is open and run after 15 minutes"
labels: ["gmail", "watcher", "background-task", "asyncio", "lifespan"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - watchers/src/gmail_watcher.py
  - backend/src/main.py
  - backend/src/api/system.py
tests:
  - "GET /api/v1/health → services.watchers.email == 'active'"
---

## Prompt

I want to you make gmail watcher run by default when the frontend is open and run after 15 minutes.

## Response

Integrated Gmail watcher as an asyncio background task inside FastAPI's lifespan context manager (backend/src/main.py). Changes:

1. `watchers/src/gmail_watcher.py`: poll_interval 120 → 900 (15 minutes)
2. `backend/src/main.py`: Added asyncio.create_task(watcher.start()) in lifespan, gated on settings.gmail_client_id (pydantic-settings reads .env). Graceful cancel on shutdown.
3. `backend/src/api/system.py`: /health now checks app.state.gmail_watcher._running for real email watcher status instead of hardcoded "inactive".

Fixed: os.getenv("GMAIL_CLIENT_ID") doesn't read pydantic-settings .env file; replaced with settings.gmail_client_id.

Verified: GET /api/v1/health returns "email": "active". Backend restarts cleanly with --reload.

## Outcome

Gmail watcher starts automatically with the backend process (no Docker/separate terminal needed), polls every 15 minutes, and health endpoint reflects live status.
