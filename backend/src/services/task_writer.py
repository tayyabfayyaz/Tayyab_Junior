"""T015: Task file writer — generate structured Markdown task files with YAML frontmatter."""

from datetime import datetime, timezone
from pathlib import Path

import yaml

from backend.src.models.task import TaskCreate, TaskStatus, TaskType


def _next_task_id(task_dir: Path) -> str:
    """Generate task ID in YYYY-MM-DD-NNN format."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    existing = []
    for status_dir in task_dir.iterdir():
        if status_dir.is_dir():
            for f in status_dir.glob("*.md"):
                if f.stem.startswith(today):
                    try:
                        seq = int(f.stem.split("-")[-1])
                        existing.append(seq)
                    except ValueError:
                        pass
    next_seq = max(existing, default=0) + 1
    return f"{today}-{next_seq:03d}"


APPROVAL_REQUIRED_TYPES = {
    TaskType.SOCIAL_POST,
    TaskType.SOCIAL_REPLY,
    TaskType.EMAIL_REPLY,
    TaskType.EMAIL_DRAFT,
}


def write_task_file(
    task_data: TaskCreate,
    task_dir: Path,
    auto_approve: bool = False,
) -> tuple[str, Path]:
    """Create a new task file. Sensitive tasks go to awaiting_approval/, others to need_action/.
    Pass auto_approve=True to skip the approval queue (used for automated watcher responses).
    """
    task_id = _next_task_id(task_dir)
    now = datetime.now(timezone.utc).isoformat()

    frontmatter = {
        "task_id": task_id,
        "type": task_data.type.value,
        "priority": task_data.priority.value,
        "source": task_data.source.value,
        "created_at": now,
        "updated_at": now,
        "retry_count": 0,
    }
    if task_data.source_ref:
        frontmatter["source_ref"] = task_data.source_ref

    yaml_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)

    body_parts = [f"# Task: {task_id}", "", "## Context", task_data.context or "No context provided.", ""]
    body_parts += ["## Instruction", task_data.instruction, ""]

    if task_data.constraints:
        body_parts += ["## Constraints", task_data.constraints, ""]

    if task_data.expected_output:
        body_parts += ["## Expected Output", task_data.expected_output, ""]

    content = f"---\n{yaml_str}---\n\n" + "\n".join(body_parts) + "\n"

    needs_approval = (task_data.type in APPROVAL_REQUIRED_TYPES) and not auto_approve
    dest_dir = task_dir / ("awaiting_approval" if needs_approval else "need_action")
    dest_dir.mkdir(parents=True, exist_ok=True)
    file_path = dest_dir / f"{task_id}.md"
    file_path.write_text(content, encoding="utf-8")

    return task_id, file_path
