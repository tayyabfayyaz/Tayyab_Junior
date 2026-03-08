"""T024: Executor polling loop — scan need_action directory, pick oldest file (FIFO)."""

from pathlib import Path
from typing import Optional

import yaml


def pick_next_task(task_dir: str) -> Optional[Path]:
    """Scan tasks/need_action/ and return the oldest task file path, or None."""
    need_action = Path(task_dir) / "need_action"
    if not need_action.exists():
        return None

    task_files = sorted(need_action.glob("*.md"))
    if not task_files:
        return None

    # Sort by created_at from frontmatter for true FIFO
    def get_created_at(f: Path) -> str:
        try:
            raw = f.read_text(encoding="utf-8")
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                meta = yaml.safe_load(parts[1])
                return str(meta.get("created_at", ""))
        except Exception:
            pass
        return f.stem

    task_files.sort(key=get_created_at)
    return task_files[0]
