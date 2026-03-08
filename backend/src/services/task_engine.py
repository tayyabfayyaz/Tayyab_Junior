"""T016: Task lifecycle manager — directory-based state transitions, listing, lookup, JSONL logging."""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.src.models.task import TaskResponse, TaskStatus, TaskType, TaskPriority, TaskSource
from backend.src.services.task_parser import parse_task_file


STATUS_DIRS = {
    TaskStatus.AWAITING_APPROVAL: "awaiting_approval",
    TaskStatus.NEED_ACTION: "need_action",
    TaskStatus.PROCESSING: "processing",
    TaskStatus.DONE: "done",
    TaskStatus.FAILED: "failed",
}


class TaskEngine:
    def __init__(self, task_dir: str, log_dir: str):
        self.task_dir = Path(task_dir)
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        for d in STATUS_DIRS.values():
            (self.task_dir / d).mkdir(parents=True, exist_ok=True)

    def _log_transition(self, task_id: str, from_status: str, to_status: str, actor: str = "system", detail: str = ""):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "from_status": from_status,
            "to_status": to_status,
            "actor": actor,
            "detail": detail,
        }
        log_path = self.log_dir / "task-transitions.jsonl"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[TaskType] = None,
        priority: Optional[TaskPriority] = None,
        source: Optional[TaskSource] = None,
        limit: int = 50,
        offset: int = 0,
        sort: str = "created_at:desc",
    ) -> tuple[list[TaskResponse], int]:
        """List tasks with filtering, sorting, and pagination."""
        tasks: list[TaskResponse] = []

        statuses = [status] if status else list(TaskStatus)
        for s in statuses:
            dir_name = STATUS_DIRS[s]
            dir_path = self.task_dir / dir_name
            if not dir_path.exists():
                continue
            for f in dir_path.glob("*.md"):
                task = parse_task_file(f, s)
                if task is None:
                    continue
                if task_type and task.type != task_type:
                    continue
                if priority and task.priority != priority:
                    continue
                if source and task.source != source:
                    continue
                tasks.append(task)

        # Sort
        sort_field, sort_dir = sort.split(":") if ":" in sort else (sort, "desc")
        reverse = sort_dir == "desc"
        tasks.sort(key=lambda t: getattr(t, sort_field, t.created_at), reverse=reverse)

        total = len(tasks)
        return tasks[offset : offset + limit], total

    def get_task(self, task_id: str) -> Optional[TaskResponse]:
        """Lookup a task by ID across all directories."""
        for status, dir_name in STATUS_DIRS.items():
            file_path = self.task_dir / dir_name / f"{task_id}.md"
            if file_path.exists():
                return parse_task_file(file_path, status)
        return None

    def move_task(self, task_id: str, to_status: TaskStatus, actor: str = "system", detail: str = "") -> bool:
        """Move a task file to a new status directory (atomic)."""
        # Find current location
        for status, dir_name in STATUS_DIRS.items():
            src = self.task_dir / dir_name / f"{task_id}.md"
            if src.exists():
                dest_dir = self.task_dir / STATUS_DIRS[to_status]
                dest = dest_dir / f"{task_id}.md"

                # Update the updated_at timestamp in the file
                content = src.read_text(encoding="utf-8")
                now = datetime.now(timezone.utc).isoformat()
                import re
                content = re.sub(
                    r'updated_at:\s*"[^"]*"',
                    f'updated_at: "{now}"',
                    content,
                )

                dest.write_text(content, encoding="utf-8")
                src.unlink()

                self._log_transition(task_id, dir_name, STATUS_DIRS[to_status], actor, detail)
                return True
        return False

    def count_by_status(self) -> dict[str, int]:
        """Count tasks per status directory."""
        counts = {}
        for status, dir_name in STATUS_DIRS.items():
            dir_path = self.task_dir / dir_name
            if dir_path.exists():
                counts[dir_name] = len(list(dir_path.glob("*.md")))
            else:
                counts[dir_name] = 0
        return counts

    def count_by_type(self) -> dict[str, int]:
        """Count tasks by type across all directories."""
        counts: dict[str, int] = {}
        for status in TaskStatus:
            dir_path = self.task_dir / STATUS_DIRS[status]
            if not dir_path.exists():
                continue
            for f in dir_path.glob("*.md"):
                task = parse_task_file(f, status)
                if task:
                    counts[task.type.value] = counts.get(task.type.value, 0) + 1
        return counts
