"""T025: Executor memory loader — read relevant memory documents from vault."""

from pathlib import Path
from typing import Optional


# Map task types to relevant memory categories
TYPE_MEMORY_MAP = {
    "email_reply": ["preferences", "clients", "tone"],
    "email_draft": ["preferences", "clients", "tone"],
    "social_post": ["tone", "knowledge"],
    "social_reply": ["tone", "knowledge"],
    "whatsapp_reply": ["preferences", "clients"],
    "coding_task": ["knowledge"],
    "general": ["knowledge", "preferences"],
    "spec_generation": ["knowledge"],
}


def load_memory(memory_dir: str, task_type: str, task_source: Optional[str] = None) -> str:
    """Load relevant memory documents based on task type and source.
    Returns concatenated context string scoped by category.
    """
    vault = Path(memory_dir)
    if not vault.exists():
        return ""

    categories = TYPE_MEMORY_MAP.get(task_type, ["knowledge"])
    context_parts: list[str] = []

    for category in categories:
        cat_dir = vault / category
        if not cat_dir.exists():
            continue
        for md_file in sorted(cat_dir.glob("*.md")):
            try:
                content = md_file.read_text(encoding="utf-8")
                context_parts.append(f"--- Memory [{category}/{md_file.name}] ---\n{content}")
            except Exception:
                continue

    return "\n\n".join(context_parts)
