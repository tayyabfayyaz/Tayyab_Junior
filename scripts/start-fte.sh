#!/usr/bin/env bash
# FTE — start all services (backend, frontend, executor, watchers)
# Run once: chmod +x scripts/start-fte.sh
# Auto-start: add `bash /mnt/d/hackathon-FTE/scripts/start-fte.sh` to ~/.bashrc or Windows Task Scheduler

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

# Load environment
if [ -f "$ROOT/.env" ]; then
  export $(grep -v '^#' "$ROOT/.env" | grep -v '^$' | xargs)
fi

cd "$ROOT"

echo "[FTE] Starting all services from $ROOT ..."

# ── Backend (FastAPI / uvicorn) ──────────────────────────────────────────────
if lsof -ti:8000 > /dev/null 2>&1; then
  echo "[FTE] Backend already running on :8000"
else
  nohup uvicorn backend.src.main:app \
    --host 0.0.0.0 --port 8000 --reload \
    > "$LOG_DIR/backend-dev.log" 2>&1 &
  echo "[FTE] Backend started (PID $!)"
fi

# ── Frontend (Next.js) — always claim port 3000 ──────────────────────────────
# lsof misses WSL processes; ss is reliable. Force-kill every next-server on
# ports 3000-3009 so the new instance always binds to :3000.
echo "[FTE] Clearing ports 3000-3009 for frontend ..."
_stale_pids=$(ss -tlnp 2>/dev/null | grep -oE ":300[0-9][^,]*(pid=[0-9]+)" | grep -oE "pid=[0-9]+" | grep -oE "[0-9]+" | sort -u || true)
for _pid in $_stale_pids; do
  kill -9 "$_pid" 2>/dev/null || true
  echo "[FTE] Killed stale process (PID $_pid)"
done
[ -n "$_stale_pids" ] && sleep 2 || true
nohup bash -c "cd $ROOT/frontend && npm run dev" \
  > "$LOG_DIR/frontend-dev.log" 2>&1 &
echo "[FTE] Frontend started (PID $!) on :3000"

# ── MCP Server (tool dispatch: email, social, shell, files) ──────────────────
if lsof -ti:8001 > /dev/null 2>&1; then
  echo "[FTE] MCP Server already running on :8001"
else
  nohup python3 -m mcp_server.src.main \
    > "$LOG_DIR/mcp-server.log" 2>&1 &
  echo "[FTE] MCP Server started (PID $!)"
fi

# ── Executor ─────────────────────────────────────────────────────────────────
if pgrep -f "executor.src.main" > /dev/null 2>&1; then
  echo "[FTE] Executor already running"
else
  nohup python3 -m executor.src.main \
    > "$LOG_DIR/executor.log" 2>&1 &
  echo "[FTE] Executor started (PID $!)"
fi

# ── Watchers ─────────────────────────────────────────────────────────────────
if pgrep -f "watchers.src.main" > /dev/null 2>&1; then
  echo "[FTE] Watchers already running"
else
  nohup python3 -m watchers.src.main \
    > "$LOG_DIR/watchers.log" 2>&1 &
  echo "[FTE] Watchers started (PID $!)"
fi

# ── CEO Assistant ─────────────────────────────────────────────────────────────
if pgrep -f "ceo_assistant.src.main" > /dev/null 2>&1; then
  echo "[FTE] CEO Assistant already running"
else
  nohup python3 -m ceo_assistant.src.main \
    > "$LOG_DIR/ceo-assistant.log" 2>&1 &
  echo "[FTE] CEO Assistant started (PID $!)"
fi

# ── ngrok (WhatsApp webhook tunnel — static domain) ──────────────────────────
NGROK_BIN="$HOME/bin/ngrok"
NGROK_DOMAIN="nonflammable-nontemperamental-williemae.ngrok-free.dev"
if ! pgrep -f "ngrok start fte-backend" > /dev/null 2>&1; then
  if [ -x "$NGROK_BIN" ]; then
    nohup "$NGROK_BIN" start fte-backend --log=stdout \
      > "$LOG_DIR/ngrok.log" 2>&1 &
    echo "[FTE] ngrok tunnel started (PID $!)"
    sleep 4
  else
    echo "[FTE] ngrok not found at $NGROK_BIN — skipping tunnel"
  fi
else
  echo "[FTE] ngrok already running"
fi

NGROK_URL="https://$NGROK_DOMAIN"

echo ""
echo "[FTE] All services launched."
echo "  Frontend      → http://localhost:3000"
echo "  Backend       → http://localhost:8000"
echo "  MCP Server    → tcp://localhost:8001"
echo "  CEO Reports   → http://localhost:3000/reports"
echo "  Logs          → $LOG_DIR/"
if [ -n "$NGROK_URL" ]; then
  echo ""
  echo "  ┌─────────────────────────────────────────────────────────────┐"
  echo "  │  WhatsApp Webhook URL (set this in Meta for Developers):    │"
  echo "  │  $NGROK_URL/api/v1/webhooks/whatsapp"
  echo "  │  Verify Token: fte-whatsapp-verify-2026                     │"
  echo "  └─────────────────────────────────────────────────────────────┘"
fi
