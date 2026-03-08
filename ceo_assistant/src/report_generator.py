"""CEO Assistant — collect task data and generate daily markdown report."""

import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import yaml

from ceo_assistant.src.config import config


def _extract_section(content: str, heading: str) -> Optional[str]:
    pattern = rf"##\s+{re.escape(heading)}\s*\n(.*?)(?=\n##\s|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def _parse_task_file(file_path: Path) -> Optional[dict]:
    """Parse a task markdown file into a plain dict (no backend model dependency)."""
    try:
        raw = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

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
    return {
        "task_id": str(meta.get("task_id", file_path.stem)),
        "type": meta.get("type", "general"),
        "priority": meta.get("priority", "medium"),
        "source": meta.get("source", "frontend"),
        "created_at": str(meta.get("created_at", "")),
        "updated_at": str(meta.get("updated_at", "")),
        "retry_count": int(meta.get("retry_count", 0)),
        "result": _extract_section(body, "Result"),
        "error": _extract_section(body, "Error"),
        "instruction": _extract_section(body, "Instruction") or "",
    }


def _tasks_in_period(directory: Path, since: datetime) -> list[dict]:
    """Return all tasks in directory updated at or after `since`."""
    tasks = []
    if not directory.exists():
        return tasks
    for f in directory.glob("*.md"):
        task = _parse_task_file(f)
        if task is None:
            continue
        updated_raw = task.get("updated_at", "")
        try:
            updated = datetime.fromisoformat(updated_raw)
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
        if updated >= since:
            tasks.append(task)
    return tasks


def generate_report(reports_dir: str = None, task_dir: str = None) -> Path:
    """Collect last-24h task data and write a dated report markdown file.

    Returns the path of the written report file.
    """
    reports_path = Path(reports_dir or config.reports_dir)
    task_path = Path(task_dir or config.task_dir)
    reports_path.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    period_start = now - timedelta(hours=24)
    date_str = now.strftime("%Y-%m-%d")
    report_id = date_str

    done_tasks = _tasks_in_period(task_path / "done", period_start)
    failed_tasks = _tasks_in_period(task_path / "failed", period_start)
    all_tasks = done_tasks + failed_tasks

    total = len(all_tasks)
    completed = len(done_tasks)
    failed = len(failed_tasks)
    success_rate = round((completed / total * 100) if total > 0 else 0, 1)

    # Breakdown by source
    by_source: dict[str, dict] = defaultdict(lambda: {"done": 0, "failed": 0})
    for t in done_tasks:
        by_source[t["source"]]["done"] += 1
    for t in failed_tasks:
        by_source[t["source"]]["failed"] += 1

    # Breakdown by type
    by_type: dict[str, int] = defaultdict(int)
    for t in all_tasks:
        by_type[t["type"]] += 1

    # Build markdown
    title = f"CEO Daily Report — {now.strftime('%B %d, %Y')}"

    frontmatter = {
        "report_id": report_id,
        "generated_at": now.isoformat(),
        "period_start": period_start.isoformat(),
        "period_end": now.isoformat(),
        "total_tasks": total,
        "completed": completed,
        "failed": failed,
    }

    lines = [
        "---",
        yaml.dump(frontmatter, default_flow_style=False).strip(),
        "---",
        "",
        f"# {title}",
        "",
        "## Executive Summary",
        "",
    ]

    if total == 0:
        lines.append("No tasks were processed in the last 24 hours.")
    else:
        lines.append(
            f"{total} task{'s' if total != 1 else ''} processed in the last 24 hours. "
            f"{completed} completed successfully ({success_rate}% success rate)"
            + (f", {failed} failed." if failed else ".")
        )

    lines += ["", "## Task Breakdown by Source", ""]
    if by_source:
        lines.append("| Source | Done | Failed | Total |")
        lines.append("|--------|------|--------|-------|")
        for src, counts in sorted(by_source.items()):
            row_total = counts["done"] + counts["failed"]
            lines.append(f"| {src} | {counts['done']} | {counts['failed']} | {row_total} |")
    else:
        lines.append("_No activity._")

    lines += ["", "## Task Breakdown by Type", ""]
    if by_type:
        lines.append("| Type | Count |")
        lines.append("|------|-------|")
        for ttype, count in sorted(by_type.items(), key=lambda x: -x[1]):
            lines.append(f"| {ttype} | {count} |")
    else:
        lines.append("_No activity._")

    lines += ["", f"## Completed Tasks ({completed})", ""]
    if done_tasks:
        for t in sorted(done_tasks, key=lambda x: x.get("updated_at", ""), reverse=True):
            result_preview = ""
            if t.get("result"):
                result_preview = " — " + t["result"][:120].replace("\n", " ")
                if len(t["result"]) > 120:
                    result_preview += "..."
            lines.append(f"- **[{t['task_id']}]** `{t['type']}` from `{t['source']}`{result_preview}")
    else:
        lines.append("_No completed tasks._")

    lines += ["", f"## Failed Tasks ({failed})", ""]
    if failed_tasks:
        for t in sorted(failed_tasks, key=lambda x: x.get("updated_at", ""), reverse=True):
            error_preview = ""
            if t.get("error"):
                error_preview = " — " + t["error"][:120].replace("\n", " ")
                if len(t["error"]) > 120:
                    error_preview += "..."
            lines.append(f"- **[{t['task_id']}]** `{t['type']}` from `{t['source']}`{error_preview}")
    else:
        lines.append("_No failed tasks._")

    lines.append("")

    content = "\n".join(lines)
    report_path = reports_path / f"{report_id}.md"
    report_path.write_text(content, encoding="utf-8")

    print(f"[ceo-assistant] Report written: {report_path}")
    return report_path
