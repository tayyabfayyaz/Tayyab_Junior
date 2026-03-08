---
id: 008
title: Watcher Auto-Start Scripts on Boot
stage: general
date: 2026-02-28
surface: agent
model: claude-sonnet-4-6
feature: none
branch: main
user: fayaztayyab684
command: "write auto activate script for watcher when laptop is on"
labels: ["autostart","watchers","wsl2","task-scheduler","gmail","startup"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - scripts/start-watchers.sh
  - scripts/setup-autostart.sh
  - scripts/fte-launcher.vbs
  - scripts/status.sh
tests:
  - null
---

## Prompt

write the auto acivate script for the watcher when The laptop is on so firstly activate the watcher to watch the email and reply them.

## Response snapshot

Created 4 files to auto-start FTE watchers on every Windows/WSL2 boot:

1. `scripts/start-watchers.sh` — Smart health-checked startup script. Starts backend, MCP server, watchers, executor, CEO assistant. Skips already-running processes. Logs to logs/autostart.log.

2. `scripts/setup-autostart.sh` — One-time installer with 3 methods:
   - Method 1: /etc/wsl.conf [boot] command (runs on WSL start)
   - Method 2: Windows Task Scheduler (fires 30s after Windows login)
   - Method 3: Windows Startup folder via fte-launcher.vbs (manual fallback)

3. `scripts/fte-launcher.vbs` — Silent Windows VBScript launcher. Waits 30s then runs WSL bash start-watchers.sh with no visible console window.

4. `scripts/status.sh` — Live status checker showing all service states, task queue counts, and last watcher event.

## Outcome

- ✅ Impact: Watchers auto-start on every laptop boot via dual mechanism (WSL boot + Task Scheduler). Gmail watcher resumes from last processed IDs immediately.
- 🧪 Tests: null
- 📁 Files: 4 scripts created and marked executable
- 🔁 Next prompts: Run setup-autostart.sh once to install, then test with status.sh
- 🧠 Reflection: Used dual-mechanism approach (wsl.conf + Task Scheduler) for reliability — if one fails, the other catches it. Health checks prevent duplicate processes.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): null
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): Add email notification on watcher startup failure
