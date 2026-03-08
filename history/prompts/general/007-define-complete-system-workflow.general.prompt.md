---
id: 007
title: Define Complete System Workflow
stage: general
date: 2026-02-28
surface: agent
model: claude-sonnet-4-6
feature: none
branch: main
user: fayaztayyab684
command: "create the md file and define complete workflow"
labels: ["workflow","documentation","architecture","watchers","executor","mcp"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - WORKFLOW.md
tests:
  - null
---

## Prompt

create the md file and define complete the work flow. Means define the first action watcher action and other proccess.

## Response snapshot

Created `/mnt/d/hackathon-FTE/WORKFLOW.md` — a comprehensive 18-section workflow document covering:

1. System Architecture Overview (ASCII diagram of full stack)
2. Component Map (table of all 7 services)
3. Task Lifecycle State Machine (need_action → awaiting_approval → processing → done/failed)
4. Workflow 1: Gmail Watcher → Task → Email Reply (10 steps)
5. Workflow 2: WhatsApp Webhook → Task → Notification
6. Workflow 3: Social Watcher → Task → Post
7. Workflow 4: GitHub Webhook → Coding Task
8. Workflow 5: Manual Frontend Task
9. Workflow 6: CEO Daily Report (scheduler-driven)
10. Executor Deep-Dive (polling loop, memory load, Claude invocation, result write)
11. MCP Tool Layer (email, messaging, social, files, shell)
12. Memory Vault (structure, loading rules by task type)
13. Approval Gate Process (which tasks require human approval)
14. Notification Routing (Gmail, WhatsApp, LinkedIn, Twitter)
15. Logging & Audit Trail (JSONL format)
16. Environment & Configuration Reference (all env vars)
17. Error Handling & Retry Policy (3-attempt backoff)
18. Directory Structure at Runtime

## Outcome

- ✅ Impact: Full system workflow documented in a single reference file; covers all ingestion paths (Gmail, WhatsApp, Social, GitHub, Frontend, Scheduler) with step-by-step flow
- 🧪 Tests: null
- 📁 Files: WORKFLOW.md (created, ~550 lines)
- 🔁 Next prompts: Add sequence diagrams (Mermaid), link from README, add OAuth setup workflow
- 🧠 Reflection: Explored the entire codebase before writing to ensure accuracy — watcher poll intervals, approval gate logic, notification routing, and retry policy all verified against source code

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): null
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): Add Mermaid sequence diagrams to each workflow section
