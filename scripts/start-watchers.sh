#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# FTE — Watcher Auto-Start Script
# Starts Gmail watcher, executor, backend, and MCP server.
# Safe to call repeatedly — skips anything already running.
#
# Usage:
#   bash /mnt/d/hackathon-FTE/scripts/start-watchers.sh
#
# Auto-start setup (run once):
#   bash /mnt/d/hackathon-FTE/scripts/setup-autostart.sh
# ─────────────────────────────────────────────────────────────────────────────

set -uo pipefail

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/logs"
STARTUP_LOG="$LOG_DIR/autostart.log"
PID_FILE="$LOG_DIR/fte.pids"

mkdir -p "$LOG_DIR"
mkdir -p "$ROOT/tasks/need_action"
mkdir -p "$ROOT/tasks/awaiting_approval"
mkdir -p "$ROOT/tasks/processing"
mkdir -p "$ROOT/tasks/done"
mkdir -p "$ROOT/tasks/failed"
mkdir -p "$ROOT/memory"

# ── Logging helper ───────────────────────────────────────────────────────────
log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  echo "$msg"
  echo "$msg" >> "$STARTUP_LOG"
}

# ── Load .env ────────────────────────────────────────────────────────────────
if [ -f "$ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source <(grep -v '^#' "$ROOT/.env" | grep -v '^$')
  set +a
  log "Environment loaded from .env"
else
  log "WARNING: .env not found at $ROOT/.env — some services may not start"
fi

cd "$ROOT"

# ── Prerequisite checks ──────────────────────────────────────────────────────
log "──────────────────────────────────────────────"
log "FTE Watcher Auto-Start"
log "Root: $ROOT"
log "──────────────────────────────────────────────"

# Check Python
if ! command -v python3 &>/dev/null; then
  log "ERROR: python3 not found. Install Python 3.10+ first."
  exit 1
fi

# Check Anthropic API key (required for email classification + executor)
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  log "WARNING: ANTHROPIC_API_KEY not set — Claude classification will be skipped."
fi

# Check Gmail credentials
GMAIL_TOKEN="${MEMORY_DIR:-./memory}/gmail_token.json"
if [ ! -f "$GMAIL_TOKEN" ]; then
  log "WARNING: Gmail token not found at $GMAIL_TOKEN"
  log "         Run: python3 scripts/gmail_oauth_setup.py"
fi

# Check Gmail client ID (required to activate watcher)
if [ -z "${GMAIL_CLIENT_ID:-}" ]; then
  log "WARNING: GMAIL_CLIENT_ID not set in .env — Gmail watcher will not start."
fi

# ── Process check helper ─────────────────────────────────────────────────────
is_running() {
  pgrep -f "$1" > /dev/null 2>&1
}

port_in_use() {
  ss -tlnp 2>/dev/null | grep -q ":$1 " || lsof -ti:"$1" > /dev/null 2>&1
}

# ── 1. Backend (FastAPI) ─────────────────────────────────────────────────────
if port_in_use 8000; then
  log "[backend] Already running on :8000 — skip"
else
  log "[backend] Starting FastAPI backend..."
  nohup python3 -m uvicorn backend.src.main:app \
    --host 0.0.0.0 --port 8000 \
    >> "$LOG_DIR/backend-dev.log" 2>&1 &
  BACKEND_PID=$!
  echo "backend=$BACKEND_PID" >> "$PID_FILE"
  log "[backend] Started (PID $BACKEND_PID)"
  sleep 2  # give backend time to bind port before watchers connect
fi

# ── 2. MCP Server ────────────────────────────────────────────────────────────
if port_in_use 8001; then
  log "[mcp-server] Already running on :8001 — skip"
else
  log "[mcp-server] Starting MCP tool server..."
  nohup python3 -m mcp_server.src.main \
    >> "$LOG_DIR/mcp-server.log" 2>&1 &
  MCP_PID=$!
  echo "mcp=$MCP_PID" >> "$PID_FILE"
  log "[mcp-server] Started (PID $MCP_PID)"
fi

# ── 3. Watcher (Gmail + Social + Scheduler) ──────────────────────────────────
if is_running "watchers.src.main"; then
  log "[watchers] Already running — skip"
else
  log "[watchers] Starting watcher daemon..."
  nohup python3 -m watchers.src.main \
    >> "$LOG_DIR/watchers.log" 2>&1 &
  WATCHER_PID=$!
  echo "watchers=$WATCHER_PID" >> "$PID_FILE"
  log "[watchers] Started (PID $WATCHER_PID)"
fi

# ── 4. Executor (Claude task runner) ─────────────────────────────────────────
if is_running "executor.src.main"; then
  log "[executor] Already running — skip"
else
  log "[executor] Starting executor daemon..."
  nohup python3 -m executor.src.main \
    >> "$LOG_DIR/executor.log" 2>&1 &
  EXECUTOR_PID=$!
  echo "executor=$EXECUTOR_PID" >> "$PID_FILE"
  log "[executor] Started (PID $EXECUTOR_PID)"
fi

# ── 5. CEO Assistant (optional) ──────────────────────────────────────────────
if is_running "ceo_assistant.src.main"; then
  log "[ceo-assistant] Already running — skip"
else
  log "[ceo-assistant] Starting CEO assistant..."
  nohup python3 -m ceo_assistant.src.main \
    >> "$LOG_DIR/ceo-assistant.log" 2>&1 &
  CEO_PID=$!
  echo "ceo=$CEO_PID" >> "$PID_FILE"
  log "[ceo-assistant] Started (PID $CEO_PID)"
fi

# ── Health check (after 5 seconds) ───────────────────────────────────────────
sleep 5

log ""
log "─── Service Health Check ──────────────────────"
port_in_use 8000  && log "[backend]      ✅ Running on :8000" \
                   || log "[backend]      ❌ NOT running — check $LOG_DIR/backend-dev.log"
port_in_use 8001  && log "[mcp-server]   ✅ Running on :8001" \
                   || log "[mcp-server]   ⚠️  Not running (optional)"
is_running "watchers.src.main" \
                  && log "[watchers]     ✅ Running" \
                   || log "[watchers]     ❌ NOT running — check $LOG_DIR/watchers.log"
is_running "executor.src.main" \
                  && log "[executor]     ✅ Running" \
                   || log "[executor]     ❌ NOT running — check $LOG_DIR/executor.log"

log "──────────────────────────────────────────────"
log "Gmail watcher polls every 15 min for unread important emails."
log "Tasks appear at: $ROOT/tasks/"
log "Full log:        $STARTUP_LOG"
log "PIDs recorded:   $PID_FILE"
log "──────────────────────────────────────────────"
