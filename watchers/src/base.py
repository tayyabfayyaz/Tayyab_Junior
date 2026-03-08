"""T054: Base watcher class — abstract base with lifecycle, polling, event logging."""

import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class BaseWatcher(ABC):
    """Abstract base class for all platform watchers."""

    def __init__(self, name: str, poll_interval: int = 60, log_dir: str = "./logs"):
        self.name = name
        self.poll_interval = poll_interval
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._running = False

    def log_event(
        self,
        watcher_type: str,
        raw_payload: dict,
        action_required: bool,
        task_id: Optional[str] = None,
    ):
        """Log a watcher event to JSONL."""
        event = {
            "event_id": str(uuid.uuid4())[:8],
            "watcher_type": watcher_type,
            "raw_payload": raw_payload,
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "action_required": action_required,
            "task_id": task_id,
        }
        log_path = self.log_dir / "watcher-events.jsonl"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

    @abstractmethod
    async def poll(self):
        """Execute one polling cycle. Subclasses implement platform-specific logic."""
        pass

    async def start(self):
        """Start the polling loop."""
        self._running = True
        print(f"[{self.name}] Watcher started (interval: {self.poll_interval}s)")
        while self._running:
            try:
                await self.poll()
            except Exception as e:
                print(f"[{self.name}] Error: {e}")
            await asyncio.sleep(self.poll_interval)

    def stop(self):
        """Stop the polling loop."""
        self._running = False
        print(f"[{self.name}] Watcher stopped")

    def health(self) -> dict:
        """Return health status."""
        return {
            "name": self.name,
            "running": self._running,
            "poll_interval": self.poll_interval,
        }
