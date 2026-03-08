#!/usr/bin/env bash
# FTE — Live status check for all services

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/logs"

is_running() { pgrep -f "$1" > /dev/null 2>&1; }
port_in_use() { ss -tlnp 2>/dev/null | grep -q ":$1 " || lsof -ti:"$1" > /dev/null 2>&1; }
check() {
  local label="$1" test_fn="$2" test_arg="$3"
  if $test_fn "$test_arg"; then
    printf "  ✅  %-22s running\n" "$label"
  else
    printf "  ❌  %-22s NOT running\n" "$label"
  fi
}

echo ""
echo "══════════════════════════════════════════"
echo " FTE Service Status  $(date '+%Y-%m-%d %H:%M:%S')"
echo "══════════════════════════════════════════"
check "Backend (:8000)"   port_in_use  8000
check "MCP Server (:8001)" port_in_use 8001
check "Watchers"           is_running  "watchers.src.main"
check "Executor"           is_running  "executor.src.main"
check "CEO Assistant"      is_running  "ceo_assistant.src.main"
echo ""

echo " Task Queue:"
for dir in need_action awaiting_approval processing done failed; do
  count=$(find "$ROOT/tasks/$dir" -name "*.md" 2>/dev/null | wc -l)
  printf "   %-22s %d tasks\n" "$dir" "$count"
done
echo ""

echo " Last watcher event:"
if [ -f "$LOG_DIR/watcher-events.jsonl" ]; then
  tail -1 "$LOG_DIR/watcher-events.jsonl" | python3 -c "
import sys, json
try:
    e = json.loads(sys.stdin.read())
    print(f\"  {e.get('detected_at','')}  [{e.get('watcher_type','')}]  action={e.get('action_required','')}  task={e.get('task_id','none')}\")
except: print('  (could not parse)')
"
else
  echo "  (no events yet)"
fi
echo ""

echo " Last autostart log:"
if [ -f "$LOG_DIR/autostart.log" ]; then
  tail -3 "$LOG_DIR/autostart.log" | sed 's/^/  /'
else
  echo "  (not started via autostart yet)"
fi
echo "══════════════════════════════════════════"
