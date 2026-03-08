# Watcher Troubleshooting

## Table of Contents
1. [Diagnosis Flow](#diagnosis-flow)
2. [Common Failure Modes](#common-failure-modes)
3. [Restarting Watchers](#restarting-watchers)
4. [Resetting State](#resetting-state)
5. [Watcher-Specific Issues](#watcher-specific-issues)

---

## Diagnosis Flow

When a watcher is not creating tasks, follow this sequence:

```
Step 1 — Is the watcher process alive?
    python scripts/check_health.py
    └── status "inactive" → go to Restarting Watchers
    └── status "active"  → go to Step 2

Step 2 — Has the watcher detected any events recently?
    python scripts/tail_events.py --watcher <name> --limit 10
    └── no events in last 1h → go to Step 3
    └── events present, action_required=false → watcher running but
        classifier is filtering events as "informational" (expected behavior)
    └── events present, action_required=true → tasks ARE being created;
        check tasks/need_action/ for the task files

Step 3 — Check the backend log for errors
    tail -50 logs/backend-dev.log | grep -i "error\|warn\|watcher"
    └── OAuth error → re-run OAuth setup script
    └── Rate limit / quota → watcher is throttling (wait or increase interval)
    └── No errors → watcher may be waiting for next poll (check poll_interval)

Step 4 — Verify environment variables are set
    grep -E "GMAIL_CLIENT_ID|LINKEDIN_CLIENT_ID|TWITTER_API_KEY" .env
    └── empty value → watcher won't start (by design)
```

## Common Failure Modes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Watcher shows "inactive" in health | Process not running or env var missing | Restart watchers or set missing env var |
| No Gmail tasks for hours | OAuth token expired | Re-run `scripts/gmail_oauth_setup.py` |
| Gmail watcher detects emails but no tasks created | Emails classified as "informational" | Check Claude classification logic in `watchers/src/gmail_watcher.py` |
| LinkedIn watcher never starts | `LINKEDIN_CLIENT_ID` not set | Set env var and restart |
| Scheduler creates duplicate tasks | Clock skew or multi-instance | Check for multiple watcher processes (`pgrep -f watchers`) |
| `logs/watcher-events.jsonl` empty | No watchers ran yet | Trigger a manual poll or check startup |
| `tasks/need_action/` not growing | Watcher runs but classifier rejects | Lower classification threshold or check prompt |

## Restarting Watchers

### Standalone watcher daemon
```bash
pkill -f "watchers.src.main" 2>/dev/null
nohup python3 -m watchers.src.main > logs/watchers.log 2>&1 &
echo "Watchers PID $!"
```

### Backend-embedded watchers (Gmail + Social)
Restart the backend — watchers restart automatically in lifespan:
```bash
fuser -k 8000/tcp 2>/dev/null
nohup uvicorn backend.src.main:app --host 0.0.0.0 --port 8000 --reload \
    > logs/backend-dev.log 2>&1 &
echo "Backend PID $!"
```

### All services at once
```bash
bash scripts/start-fte.sh
```

### Verify restart
```bash
sleep 5
python scripts/check_health.py
# All watchers should show "active"
```

## Resetting State

### Clear Gmail processed IDs (re-process old emails)
```bash
python3 -c "
import json
from pathlib import Path
state = Path('memory/gmail_watcher_state.json')
data = json.loads(state.read_text())
data['processed_ids'] = []
state.write_text(json.dumps(data, indent=2))
print('Gmail state cleared — watcher will re-evaluate all unread emails on next poll')
"
```

**Warning:** Clearing state may cause duplicate task creation for emails already processed. Only do this when intentionally reprocessing.

### Clear Twitter/LinkedIn state
```bash
python3 -c "
import json
from pathlib import Path
state = Path('memory/twitter_watcher_state.json')
state.write_text(json.dumps({'last_mention_id': None, 'processed_ids': []}, indent=2))
print('Twitter/Social state cleared')
"
```

## Watcher-Specific Issues

### Gmail Watcher

**Issue: OAuth token expired**
```bash
# Check token validity
python3 -c "
import json; from pathlib import Path
d = json.loads(Path('memory/gmail_token.json').read_text())
print('Has refresh_token:', bool(d.get('refresh_token')))
print('Token_uri:', d.get('token_uri', 'missing'))
"
# If missing or invalid:
python3 scripts/gmail_oauth_setup.py
```

**Issue: Watcher not finding emails**
- Check Gmail filter: watcher searches `is:unread is:important` — ensure emails are marked Important in Gmail
- Verify `GMAIL_MONITORED_EMAIL` env var matches the authenticated account

---

### LinkedIn / Social Watcher

**Issue: Not starting**
- Requires `LINKEDIN_CLIENT_ID` to be set
- Verify: `grep LINKEDIN_CLIENT_ID .env`

**Issue: Rate limited**
- LinkedIn API has strict rate limits; watcher backs off automatically
- Check `logs/backend-dev.log` for `429` responses

---

### Scheduler Watcher

**Issue: Scheduled tasks not created**
- Requires `config/schedule.json` to exist with valid schedule entries
- Check schedule format: `{"id":"...", "hour": 18, "days": [0,1,2,3,4], "platform": "linkedin", ...}`
- Verify current UTC hour matches `schedule.hour`

---

### GitHub / WhatsApp Handlers

These are **webhook-driven** (not polling) — they only fire when GitHub/WhatsApp sends a POST to the backend.

**Issue: Not receiving events**
- Verify webhook URL is reachable from the internet (ngrok for local dev)
- Check `GITHUB_WEBHOOK_SECRET` matches the secret configured in GitHub repo settings
- Check `WHATSAPP_VERIFY_TOKEN` matches Meta developer console
- Inspect incoming webhooks: `tail -f logs/backend-dev.log | grep webhook`
