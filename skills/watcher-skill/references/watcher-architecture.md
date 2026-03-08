# Watcher Architecture

## Table of Contents
1. [Base Class](#base-class)
2. [Polling Loop](#polling-loop)
3. [Event Schema](#event-schema)
4. [Task Creation Flow](#task-creation-flow)
5. [State File Formats](#state-file-formats)
6. [Watcher Startup](#watcher-startup)

---

## Base Class

All watchers extend `watchers/src/base.py:BaseWatcher`:

```python
class BaseWatcher(ABC):
    name: str           # watcher identifier (e.g. "gmail", "social")
    poll_interval: int  # seconds between polls
    _running: bool      # True while active

    async def poll(self)   # abstract — platform-specific fetch logic
    async def start(self)  # polling loop with error handling
    def stop(self)         # set _running = False
    def health(self) -> dict  # returns {"name": ..., "running": bool, "poll_interval": int}
    def log_event(watcher_type, raw_payload, action_required, task_id)
```

## Polling Loop

```
start()
└── while _running:
    ├── await poll()          ← platform-specific logic
    ├── on exception: log and continue (never crash loop)
    └── await asyncio.sleep(poll_interval)
```

Each `poll()` implementation:
1. Fetches new items from the platform API
2. Filters already-processed items (via state file or in-memory dedup)
3. For each new actionable item: calls `write_task_file()` to create a task
4. Calls `log_event()` to append to `logs/watcher-events.jsonl`
5. Updates the state file to mark items as processed

## Event Schema

Every event appended to `logs/watcher-events.jsonl`:

```json
{
  "event_id": "abc12345",
  "watcher_type": "gmail",
  "raw_payload": {
    "from": "client@example.com",
    "subject": "Re: Project update",
    "message_id": "18e3f..."
  },
  "detected_at": "2026-02-24T08:30:00+00:00",
  "action_required": true,
  "task_id": "2026-02-24-003"
}
```

| Field | Description |
|-------|-------------|
| `event_id` | Random 8-char hex ID |
| `watcher_type` | One of: `gmail`, `linkedin`, `twitter`, `github`, `whatsapp`, `scheduler` |
| `raw_payload` | Platform-specific data (varies by watcher) |
| `detected_at` | UTC ISO timestamp when event was detected |
| `action_required` | `true` if a task was created, `false` if informational only |
| `task_id` | Task ID created (or `null` if `action_required=false`) |

## Task Creation Flow

```
poll() detects new item
    │
    ├── Classify: does this require action?
    │   └── GmailWatcher: asks Claude to classify "action_required" vs "informational"
    │
    ├── If action_required=true:
    │   ├── Build TaskCreate(type, priority, source, instruction, context, ...)
    │   ├── write_task_file(task_data, task_dir)  → tasks/need_action/YYYY-MM-DD-NNN.md
    │   └── log_event(action_required=True, task_id=...)
    │
    └── If action_required=false:
        └── log_event(action_required=False, task_id=None)
```

**Task sources by watcher:**

| Watcher | TaskSource | Common TaskType |
|---------|-----------|-----------------|
| GmailWatcher | `gmail` | `email_reply`, `email_draft` |
| SocialWatcher (LinkedIn) | `linkedin` | `social_post`, `social_reply` |
| SocialWatcher (Twitter) | `twitter` | `social_post`, `social_reply` |
| GithubHandler | `github` | `coding_task`, `general` |
| WhatsAppHandler | `whatsapp` | `whatsapp_reply` |
| SchedulerWatcher | `scheduler` | `social_post` |

## State File Formats

### `memory/gmail_watcher_state.json`
```json
{
  "processed_ids": ["18e3fab12", "18e3fab13", "..."],
  "last_poll": "2026-02-24T08:30:00+00:00"
}
```
Keeps last 500 processed message IDs to prevent duplicate task creation.

### `memory/twitter_watcher_state.json`
```json
{
  "last_mention_id": "1234567890",
  "processed_ids": ["..."]
}
```

## Watcher Startup

Watchers are started in two ways:

**1. Embedded in backend (lifespan)** — `backend/src/main.py`:
```python
# GmailWatcher starts if GMAIL_CLIENT_ID is set
# SocialWatcher starts if LINKEDIN_CLIENT_ID is set
```

**2. Standalone daemon** — `watchers/src/main.py`:
```bash
python3 -m watchers.src.main
```
Starts all configured watchers based on env vars, runs until SIGINT/SIGTERM.
