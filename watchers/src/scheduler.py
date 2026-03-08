"""T061: Scheduler watcher — generate social_post tasks at scheduled times."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from watchers.src.base import BaseWatcher


class SchedulerWatcher(BaseWatcher):
    """Generate tasks based on schedule configuration."""

    def __init__(self, task_dir: str = "./tasks", log_dir: str = "./logs"):
        super().__init__(name="scheduler", poll_interval=60, log_dir=log_dir)
        self.task_dir = Path(task_dir)
        self.schedule_file = Path(os.getenv("SCHEDULE_CONFIG", "./config/schedule.json"))
        self._last_check: dict[str, str] = {}

    async def poll(self):
        """Check if any scheduled tasks need to be created."""
        if not self.schedule_file.exists():
            return

        try:
            schedules = json.loads(self.schedule_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return

        now = datetime.now(timezone.utc)

        for schedule in schedules:
            schedule_id = schedule.get("id", "")
            schedule_hour = schedule.get("hour", -1)
            schedule_days = schedule.get("days", [])  # 0=Mon, 6=Sun

            # Check if we should fire this schedule
            if now.weekday() not in schedule_days:
                continue
            if now.hour != schedule_hour:
                continue

            # Prevent duplicate creation within the same hour
            check_key = f"{schedule_id}:{now.strftime('%Y-%m-%d-%H')}"
            if check_key in self._last_check:
                continue

            self._last_check[check_key] = now.isoformat()
            await self._create_scheduled_task(schedule)

    async def _create_scheduled_task(self, schedule: dict):
        """Create a social_post task from a schedule entry."""
        from backend.src.models.task import TaskCreate, TaskSource, TaskType, TaskPriority
        from backend.src.services.task_writer import write_task_file

        platform = schedule.get("platform", "linkedin")
        guidelines = schedule.get("content_guidelines", "")
        topic = schedule.get("topic", "")

        create_data = TaskCreate(
            type=TaskType.SOCIAL_POST,
            priority=TaskPriority.MEDIUM,
            source=TaskSource.SCHEDULER,
            instruction=f"Generate and publish a {platform} post about: {topic}",
            context=f"Platform: {platform}\nContent guidelines: {guidelines}",
            constraints=schedule.get("constraints", "Professional tone, engaging content"),
        )
        task_id, _ = write_task_file(create_data, self.task_dir)
        self.log_event(
            watcher_type="scheduler",
            raw_payload=schedule,
            action_required=True,
            task_id=task_id,
        )
        print(f"[scheduler] Created scheduled task: {task_id} ({platform})")
