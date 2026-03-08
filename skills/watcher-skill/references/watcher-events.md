# Watcher Events Reference

## Table of Contents
1. [Log File Location](#log-file-location)
2. [Event Fields](#event-fields)
3. [Raw Payload Shapes per Watcher](#raw-payload-shapes)
4. [Query Patterns](#query-patterns)

---

## Log File Location

```
logs/watcher-events.jsonl    ← one JSON object per line, append-only
```

Each line is a complete JSON event. The file is never rotated automatically — it grows indefinitely.

## Event Fields

| Field | Type | Values |
|-------|------|--------|
| `event_id` | string | 8-char hex, unique per event |
| `watcher_type` | string | `gmail` \| `linkedin` \| `twitter` \| `github` \| `whatsapp` \| `scheduler` |
| `raw_payload` | object | Platform-specific (see below) |
| `detected_at` | ISO datetime | UTC timestamp of detection |
| `action_required` | boolean | `true` = task created, `false` = informational |
| `task_id` | string \| null | e.g. `"2026-02-24-003"` or `null` |

## Raw Payload Shapes

### Gmail
```json
{
  "message_id": "18e3fab12345",
  "from": "client@example.com",
  "subject": "Re: Contract review",
  "snippet": "Hi, just following up on...",
  "date": "Mon, 24 Feb 2026 08:30:00 +0000"
}
```

### LinkedIn / Twitter (Social)
```json
{
  "platform": "linkedin",
  "post_id": "urn:li:activity:1234567",
  "author": "Jane Smith",
  "content": "Excited to announce...",
  "engagement": { "likes": 42, "comments": 7 }
}
```

### GitHub
```json
{
  "event": "push",
  "repository": "org/repo",
  "ref": "refs/heads/main",
  "commits": 3,
  "pusher": "dev@example.com"
}
```

### WhatsApp
```json
{
  "from": "+1234567890",
  "message": "Can you check on the proposal?",
  "timestamp": "1708765200",
  "message_id": "wamid.abc123"
}
```

### Scheduler
```json
{
  "id": "daily-linkedin-post",
  "platform": "linkedin",
  "topic": "AI productivity tips",
  "hour": 18,
  "days": [0, 1, 2, 3, 4]
}
```

## Query Patterns

Use `scripts/tail_events.py` for all common queries. For custom queries, use Python directly:

### Count events by watcher type
```python
import json
from pathlib import Path
from collections import Counter

events = [json.loads(l) for l in Path("logs/watcher-events.jsonl").read_text().splitlines() if l.strip()]
print(Counter(e["watcher_type"] for e in events))
```

### Events that created tasks (last 24h)
```python
from datetime import datetime, timedelta, timezone
cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
recent = [e for e in events
          if e["action_required"]
          and datetime.fromisoformat(e["detected_at"]) >= cutoff]
print(f"{len(recent)} tasks created in last 24h")
for e in recent:
    print(f"  [{e['watcher_type']}] → {e['task_id']}")
```

### Events for a specific watcher
```python
gmail_events = [e for e in events if e["watcher_type"] == "gmail"]
print(f"Gmail: {len(gmail_events)} total events, "
      f"{sum(1 for e in gmail_events if e['action_required'])} tasks created")
```

### Events with no task created (informational)
```python
no_action = [e for e in events if not e["action_required"]]
# These are emails/posts classified as not requiring a response
```

### Find which task was created from a specific event
```python
task_id = "2026-02-24-003"
match = next((e for e in events if e.get("task_id") == task_id), None)
if match:
    print(f"Created by {match['watcher_type']} at {match['detected_at']}")
    print(f"Payload: {match['raw_payload']}")
```
