#!/usr/bin/env python3
"""
FTE Watcher Health Check
Fetches watcher status from the backend health API and prints a status table.

Usage:
    python scripts/check_health.py [--url http://localhost:8000]
"""

import argparse
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone


def check_health(base_url: str) -> None:
    url = f"{base_url}/api/v1/health"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
    except urllib.error.URLError as e:
        print(f"ERROR: Cannot reach backend at {url}")
        print(f"  {e}")
        print("\nIs the backend running? Try: bash scripts/start-fte.sh")
        sys.exit(1)

    services = data.get("services", {})
    watchers = services.get("watchers", {})
    task_dirs = services.get("task_dirs", {})

    # ── Header ──────────────────────────────────────────────────────
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"\n{'─'*50}")
    print(f"  FTE Watcher Health  [{now}]")
    print(f"{'─'*50}")

    # ── Watcher statuses ────────────────────────────────────────────
    print("\n  WATCHERS")
    watcher_labels = {
        "email":    "Gmail",
        "social":   "LinkedIn / Twitter",
        "whatsapp": "WhatsApp",
        "github":   "GitHub",
    }
    for key, label in watcher_labels.items():
        status = watchers.get(key, "unknown")
        icon = "✅" if status in ("active", "running") else ("⚠️ " if status == "unknown" else "❌")
        print(f"  {icon}  {label:<22} {status}")

    # ── Task queue snapshot ──────────────────────────────────────────
    print("\n  TASK QUEUE")
    for dirname, label in [
        ("need_action", "Pending"),
        ("processing",  "Processing"),
        ("done",        "Done"),
        ("failed",      "Failed"),
    ]:
        count = task_dirs.get(dirname, 0)
        print(f"  {'📋':<4} {label:<22} {count}")

    # ── Backend status ───────────────────────────────────────────────
    backend_status = data.get("status", "unknown")
    backend_ver = data.get("version", "?")
    executor = services.get("executor", "unknown")
    print(f"\n  BACKEND   {backend_status}  (v{backend_ver})")
    print(f"  EXECUTOR  {executor}")
    print(f"{'─'*50}\n")


def main():
    parser = argparse.ArgumentParser(description="Check FTE watcher health")
    parser.add_argument("--url", default="http://localhost:8000",
                        help="Backend base URL (default: http://localhost:8000)")
    args = parser.parse_args()
    check_health(args.url)


if __name__ == "__main__":
    main()
