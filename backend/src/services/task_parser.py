"""T014: Task file parser — parse Markdown+YAML frontmatter into TaskResponse models."""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from backend.src.models.task import TaskResponse, TaskStatus, TaskType, TaskPriority, TaskSource


def _extract_section(content: str, heading: str) -> Optional[str]:
    pattern = rf"##\s+{re.escape(heading)}\s*\n(.*?)(?=\n##\s|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def parse_task_file(file_path: Path, status: TaskStatus) -> Optional[TaskResponse]:
    """Parse a Markdown task file with YAML frontmatter into a TaskResponse."""
    try:
        raw = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    # Split frontmatter from body
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return None

    try:
        meta = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None

    if not isinstance(meta, dict):
        return None

    body = parts[2]

    # Extract sections from body
    context = _extract_section(body, "Context") or ""
    instruction = _extract_section(body, "Instruction") or ""
    constraints = _extract_section(body, "Constraints")
    expected_output = _extract_section(body, "Expected Output")
    result = _extract_section(body, "Result")
    error = _extract_section(body, "Error")

    task_id = meta.get("task_id", file_path.stem)
    instruction_preview = instruction[:100] + "..." if len(instruction) > 100 else instruction

    try:
        return TaskResponse(
            task_id=str(task_id),
            type=TaskType(meta.get("type", "general")),
            priority=TaskPriority(meta.get("priority", "medium")),
            source=TaskSource(meta.get("source", "frontend")),
            status=status,
            created_at=datetime.fromisoformat(str(meta.get("created_at", datetime.utcnow().isoformat()))),
            updated_at=datetime.fromisoformat(str(meta.get("updated_at", datetime.utcnow().isoformat()))),
            retry_count=int(meta.get("retry_count", 0)),
            source_ref=meta.get("source_ref"),
            context=context,
            instruction=instruction,
            constraints=constraints,
            expected_output=expected_output,
            result=result,
            error=error,
            instruction_preview=instruction_preview,
        )
    except (ValueError, KeyError):
        return None
