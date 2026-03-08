---
name: watcher-skill
description: Operate, monitor, diagnose, and manage the FTE watcher system. Use this skill when a user asks about watcher status, watcher health, watcher events, why a watcher is not detecting messages or creating tasks, how to restart a watcher, how to read or query the watcher event log, how to reset watcher state, or any other question about Gmail, LinkedIn, Twitter, GitHub, WhatsApp, or Scheduler watchers in the FTE system.
---

# Watcher Skill

Provides procedures for monitoring, diagnosing, and operating the FTE watcher daemons that ingest events from external platforms (Gmail, LinkedIn, Twitter, GitHub, WhatsApp, Scheduler) and convert them into tasks.

## Watcher Inventory

| Watcher | Source | Poll Interval | State File |
|---------|--------|---------------|------------|
| GmailWatcher | Gmail inbox (unread+important) | 15 min | `memory/gmail_watcher_state.json` |
| SocialWatcher | LinkedIn + Twitter | 15 min | `memory/twitter_watcher_state.json` |
| SchedulerWatcher | Schedule config | 60 s | none (deduplicated in-memory) |
| GithubHandler | GitHub webhooks | event-driven | none |
| WhatsAppHandler | WhatsApp webhooks | event-driven | none |

## Decision Tree

```
User task
├── "Is watcher X running / healthy?"
│   └── → Run: python scripts/check_health.py
│
├── "What events did watcher X detect recently?"
│   └── → Run: python scripts/tail_events.py --watcher <name> --limit 20
│
├── "Why isn't watcher X creating tasks?"
│   └── → See references/watcher-troubleshooting.md § Diagnosis Flow
│
├── "Show me watcher event history / count events"
│   └── → Run: python scripts/tail_events.py --stats
│
├── "Reset / clear watcher state"
│   └── → See references/watcher-troubleshooting.md § Resetting State
│
├── "How do watchers work / architecture"
│   └── → Read references/watcher-architecture.md
│
└── "Restart a watcher"
    └── → See references/watcher-troubleshooting.md § Restarting Watchers
```

## Quick Reference

**Health API:**
```bash
curl http://localhost:8000/api/v1/health
# Returns: { services: { watchers: { email, whatsapp, social, github } } }
```

**Event log path:** `logs/watcher-events.jsonl`

**Watcher process names:**
- Backend-embedded: `uvicorn backend.src.main` (runs Gmail + Social watchers)
- Standalone: `python3 -m watchers.src.main`

## Scripts

Always run scripts with `--help` first to see usage before reading source.

- `scripts/check_health.py` — fetch watcher health from backend API, print status table
- `scripts/tail_events.py` — parse `logs/watcher-events.jsonl`, filter by watcher, show stats

## Reference Files

Load these only when the quick reference above is insufficient:

- **`references/watcher-architecture.md`** — Watcher base class, polling loop, event schema, task creation flow, state file formats
- **`references/watcher-events.md`** — Full event log format, field definitions, query patterns for common questions
- **`references/watcher-troubleshooting.md`** — Diagnosis flow, restart procedures, state reset, common failure modes
