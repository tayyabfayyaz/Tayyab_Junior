---
id: "004"
title: "LinkedIn OAuth Token and Watcher Setup"
stage: general
date: "2026-02-20"
surface: agent
model: claude-sonnet-4-6
feature: none
branch: 001-fte-task-executor
user: fayaztayyab684
command: "generate linkedin access token and make linkedin watcher active"
labels: ["linkedin", "oauth", "watcher", "social", "mcp"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .env
  - memory/linkedin_token.json
  - memory/linkedin_watcher_state.json
  - backend/src/config.py
  - backend/src/main.py
  - backend/src/api/system.py
  - watchers/src/social_watcher.py
  - mcp-server/src/main.py
  - mcp_server/src/tools/social.py
tests:
  - "GET /api/v1/health → services.watchers.social == 'active'"
  - "Backend log shows [social] LinkedIn person URN resolved"
---

## Prompt

Generate the linkedin access token and make the linkedin watcher active. This watcher watch and manage the linkedin like, posting, comment, and make linkedin profile stable and active 24/7.

## Response

### Phase A — OAuth Token
- Generated auth URL via scripts/linkedin_oauth_setup.py
- User authorized via browser (Tayyab Fayyaz account)
- Exchanged code for access token (valid 59 days)
- Token saved to memory/linkedin_token.json
- LINKEDIN_ACCESS_TOKEN updated in .env

### Phase B — Code Changes
1. backend/src/config.py: Added linkedin_client_id, linkedin_client_secret, linkedin_access_token fields to Settings
2. watchers/src/social_watcher.py: Full LinkedIn polling implementation — token file loading, person URN resolution, post fetching, comment detection, task creation, seen-ID state, 15-min interval
3. backend/src/main.py: SocialWatcher started as asyncio background task in lifespan, gated on settings.linkedin_client_id
4. backend/src/api/system.py: Live social watcher status from app.state.social_watcher._running
5. mcp-server/src/main.py: Registered social_post and social_reply tools (previously unregistered bug)
6. mcp_server/src/tools/social.py: Fixed _reply_linkedin (was a placeholder), added _load_linkedin_token() helper reading from file first

## Outcome

LinkedIn watcher active and polling every 15 min. Health endpoint shows social: "active". Backend log confirms person URN resolved (EGxDh_Dxru = Tayyab Fayyaz). MCP social tools now available to executor.
