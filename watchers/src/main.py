"""T058/T064/T079: Watchers main entry point — initialize and start all active watchers."""

import asyncio
import os
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dotenv import load_dotenv

load_dotenv()

from watchers.src.gmail_watcher import GmailWatcher

shutdown = False


def handle_shutdown(signum, frame):
    global shutdown
    print(f"\nReceived signal {signum}, shutting down watchers...")
    shutdown = True


async def main():
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    task_dir = os.getenv("TASK_DIR", "./tasks")
    log_dir = os.getenv("LOG_DIR", "./logs")

    watchers = []

    # Gmail watcher
    if os.getenv("GMAIL_CLIENT_ID"):
        gmail_watcher = GmailWatcher(task_dir=task_dir, log_dir=log_dir)
        watchers.append(gmail_watcher)

    # Social media watcher — activate if any LinkedIn or Twitter credential is present
    memory_dir = Path(os.getenv("MEMORY_DIR", "./memory"))
    has_linkedin = bool(
        os.getenv("LINKEDIN_CLIENT_ID")
        or os.getenv("LINKEDIN_ACCESS_TOKEN")
        or (memory_dir / "linkedin_token.json").exists()
    )
    if has_linkedin or os.getenv("TWITTER_API_KEY"):
        try:
            from watchers.src.social_watcher import SocialWatcher
            social_watcher = SocialWatcher(task_dir=task_dir, log_dir=log_dir)
            watchers.append(social_watcher)
            print("[watchers] Social watcher activated (LinkedIn/Twitter)")
        except ImportError:
            pass

    # Scheduler watcher (Phase 6)
    try:
        from watchers.src.scheduler import SchedulerWatcher
        scheduler = SchedulerWatcher(task_dir=task_dir, log_dir=log_dir)
        watchers.append(scheduler)
    except ImportError:
        pass

    if not watchers:
        print("No watchers configured. Waiting for webhook-based events...")
        while not shutdown:
            await asyncio.sleep(10)
        return

    print(f"Starting {len(watchers)} watcher(s)...")
    tasks = [asyncio.create_task(w.start()) for w in watchers]

    while not shutdown:
        await asyncio.sleep(1)

    for w in watchers:
        w.stop()

    for t in tasks:
        t.cancel()

    print("All watchers stopped.")


if __name__ == "__main__":
    asyncio.run(main())
