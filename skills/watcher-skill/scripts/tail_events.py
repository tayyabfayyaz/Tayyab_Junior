#!/usr/bin/env python3
"""
FTE Watcher Event Log Viewer
Parses logs/watcher-events.jsonl and displays recent events.

Usage:
    python scripts/tail_events.py [--help]
    python scripts/tail_events.py --limit 20
    python scripts/tail_events.py --watcher gmail --limit 10
    python scripts/tail_events.py --stats
    python scripts/tail_events.py --task-id 2026-02-24-003
    python scripts/tail_events.py --hours 24
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


DEFAULT_LOG = Path("logs/watcher-events.jsonl")


def load_events(log_path: Path) -> list[dict]:
    if not log_path.exists():
        print(f"ERROR: Log file not found: {log_path}")
        print("Have any watchers run yet? Check backend/watcher logs.")
        sys.exit(1)
    events = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def parse_dt(s: str) -> datetime:
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return datetime.min.replace(tzinfo=timezone.utc)


def print_event(e: dict, verbose: bool = False) -> None:
    ts = parse_dt(e.get("detected_at", "")).strftime("%Y-%m-%d %H:%M")
    wtype = e.get("watcher_type", "?").upper()
    action = "✅ TASK" if e.get("action_required") else "ℹ️  INFO"
    task_id = e.get("task_id") or "—"
    print(f"  {ts}  [{wtype:<10}]  {action}  → {task_id}")
    if verbose and e.get("raw_payload"):
        payload = e["raw_payload"]
        # Print up to 3 key fields from payload
        for key in list(payload.keys())[:3]:
            val = str(payload[key])[:80]
            print(f"               {key}: {val}")


def cmd_list(events: list[dict], watcher: str | None, limit: int, hours: int | None) -> None:
    filtered = events
    if watcher:
        filtered = [e for e in filtered if e.get("watcher_type", "").lower() == watcher.lower()]
    if hours:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        filtered = [e for e in filtered if parse_dt(e.get("detected_at", "")) >= cutoff]

    # Newest first
    filtered.sort(key=lambda e: e.get("detected_at", ""), reverse=True)
    shown = filtered[:limit]

    title = f"Watcher Events"
    if watcher:
        title += f" [{watcher}]"
    if hours:
        title += f" (last {hours}h)"
    print(f"\n{'─'*60}")
    print(f"  {title}  — showing {len(shown)} of {len(filtered)}")
    print(f"{'─'*60}")
    for e in shown:
        print_event(e, verbose=True)
    print(f"{'─'*60}\n")


def cmd_stats(events: list[dict]) -> None:
    by_watcher = Counter(e.get("watcher_type", "?") for e in events)
    tasks_created = [e for e in events if e.get("action_required")]
    by_watcher_tasks = Counter(e.get("watcher_type", "?") for e in tasks_created)

    # Last event per watcher
    last_seen: dict[str, str] = {}
    for e in events:
        wt = e.get("watcher_type", "?")
        dt = e.get("detected_at", "")
        if wt not in last_seen or dt > last_seen[wt]:
            last_seen[wt] = dt

    print(f"\n{'─'*60}")
    print(f"  FTE Watcher Event Statistics  (total: {len(events)} events)")
    print(f"{'─'*60}")
    print(f"  {'Watcher':<14} {'Events':>8} {'Tasks':>8} {'Last Seen'}")
    print(f"  {'─'*14} {'─'*8} {'─'*8} {'─'*20}")
    all_watchers = sorted(set(list(by_watcher.keys()) + list(last_seen.keys())))
    for wt in all_watchers:
        total = by_watcher.get(wt, 0)
        tasks = by_watcher_tasks.get(wt, 0)
        last = last_seen.get(wt, "never")
        if last != "never":
            last = parse_dt(last).strftime("%Y-%m-%d %H:%M")
        print(f"  {wt:<14} {total:>8} {tasks:>8}   {last}")
    print(f"{'─'*60}")
    print(f"  Total tasks created by watchers: {len(tasks_created)}")

    # Last 24h breakdown
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    recent = [e for e in events if parse_dt(e.get("detected_at", "")) >= cutoff]
    recent_tasks = [e for e in recent if e.get("action_required")]
    print(f"  Events in last 24h: {len(recent)}  (tasks: {len(recent_tasks)})")
    print(f"{'─'*60}\n")


def cmd_find_task(events: list[dict], task_id: str) -> None:
    match = next((e for e in events if e.get("task_id") == task_id), None)
    if not match:
        print(f"\nNo event found for task_id: {task_id}")
        return
    print(f"\n{'─'*60}")
    print(f"  Event for task {task_id}")
    print(f"{'─'*60}")
    for key, val in match.items():
        print(f"  {key:<16} {json.dumps(val)}")
    print(f"{'─'*60}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="FTE Watcher Event Log Viewer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--log", default=str(DEFAULT_LOG),
                        help="Path to watcher-events.jsonl")
    parser.add_argument("--watcher", help="Filter by watcher type (gmail, linkedin, twitter, github, whatsapp, scheduler)")
    parser.add_argument("--limit", type=int, default=20, help="Max events to show (default: 20)")
    parser.add_argument("--hours", type=int, help="Only show events from last N hours")
    parser.add_argument("--stats", action="store_true", help="Show aggregate statistics")
    parser.add_argument("--task-id", help="Find the event that created a specific task")
    args = parser.parse_args()

    events = load_events(Path(args.log))

    if args.task_id:
        cmd_find_task(events, args.task_id)
    elif args.stats:
        cmd_stats(events)
    else:
        cmd_list(events, watcher=args.watcher, limit=args.limit, hours=args.hours)


if __name__ == "__main__":
    main()
