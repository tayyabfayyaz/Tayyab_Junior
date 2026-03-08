"""T027: Executor daemon entry point — main loop: poll, pick, move, run, move."""

import asyncio
import json
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from executor.src.config import config
from executor.src.polling import pick_next_task
from executor.src.runner import run_task

shutdown = False


def handle_shutdown(signum, frame):
    global shutdown
    print(f"\nReceived signal {signum}, shutting down gracefully...")
    shutdown = True


def _log_transition(task_id: str, from_status: str, to_status: str, detail: str = ""):
    log_path = Path(config.log_dir) / "task-transitions.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task_id": task_id,
        "from_status": from_status,
        "to_status": to_status,
        "actor": "executor",
        "detail": detail,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _move_task(task_id: str, from_dir: str, to_dir: str):
    src = Path(config.task_dir) / from_dir / f"{task_id}.md"
    dest_dir = Path(config.task_dir) / to_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{task_id}.md"
    if src.exists():
        content = src.read_text(encoding="utf-8")
        dest.write_text(content, encoding="utf-8")
        src.unlink()


async def main():
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    print("FTE Executor starting...")
    print(f"  Task dir: {config.task_dir}")
    print(f"  Memory dir: {config.memory_dir}")
    print(f"  Poll interval: {config.poll_interval}s")
    print(f"  Max retries: {config.max_retries}")

    while not shutdown:
        task_path = pick_next_task(config.task_dir)

        if task_path is None:
            await asyncio.sleep(config.poll_interval)
            continue

        task_id = task_path.stem
        print(f"[{datetime.now(timezone.utc).isoformat()}] Picked task: {task_id}")

        # Move to processing
        _move_task(task_id, "need_action", "processing")
        _log_transition(task_id, "need_action", "processing")
        print(f"  -> Processing: {task_id}")

        # Execute
        processing_path = Path(config.task_dir) / "processing" / f"{task_id}.md"
        success, result_or_error = await run_task(processing_path)

        if success:
            _move_task(task_id, "processing", "done")
            _log_transition(task_id, "processing", "done", detail="Execution successful")
            print(f"  -> Done: {task_id}")
        else:
            _move_task(task_id, "processing", "failed")
            _log_transition(task_id, "processing", "failed", detail=result_or_error[:200])
            print(f"  -> Failed: {task_id}: {result_or_error[:100]}")

    print("Executor shut down.")


if __name__ == "__main__":
    asyncio.run(main())
