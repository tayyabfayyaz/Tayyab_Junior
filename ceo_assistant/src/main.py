"""CEO Assistant — daily report scheduler daemon."""

import asyncio
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

from ceo_assistant.src.config import config
from ceo_assistant.src.report_generator import generate_report
from ceo_assistant.src.mailer import send_report

_shutdown = False


def _handle_signal(sig, frame):
    global _shutdown
    print(f"[ceo-assistant] Received signal {sig}, shutting down...")
    _shutdown = True


async def run():
    """Main loop: check every 60 s, fire report once per day at REPORT_TIME (HH:MM UTC)."""
    global _shutdown

    Path(config.reports_dir).mkdir(parents=True, exist_ok=True)

    try:
        target_h, target_m = map(int, config.report_time.split(":"))
    except ValueError:
        print(f"[ceo-assistant] Invalid REPORT_TIME '{config.report_time}', expected HH:MM. Defaulting to 18:00.")
        target_h, target_m = 18, 0

    fired_today: set[str] = set()
    print(f"[ceo-assistant] Started. Daily report scheduled at {target_h:02d}:{target_m:02d} UTC.")
    print(f"[ceo-assistant] Reports dir: {config.reports_dir}")
    if config.ceo_email:
        print(f"[ceo-assistant] CEO email: {config.ceo_email}")
    else:
        print("[ceo-assistant] CEO_EMAIL not set — reports will be saved to disk only.")

    while not _shutdown:
        now = datetime.now(timezone.utc)
        key = f"report:{now.strftime('%Y-%m-%d')}"

        if now.hour == target_h and now.minute == target_m and key not in fired_today:
            fired_today.add(key)
            print(f"[ceo-assistant] Generating daily report for {now.strftime('%Y-%m-%d')}...")
            try:
                report_path = generate_report()
                send_report(report_path)
            except Exception as e:
                print(f"[ceo-assistant] Report generation failed: {e}")

        await asyncio.sleep(60)

    print("[ceo-assistant] Stopped.")


def main():
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    asyncio.run(run())


if __name__ == "__main__":
    main()
