"""Email approval state manager — store pending approvals, process ACCEPT/REJECT via WhatsApp."""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional


_APPROVAL_TTL_HOURS = 24
_STATE_FILE = Path(os.getenv("MEMORY_DIR", "./memory")) / "pending_email_approvals.json"


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"pending": [], "counter": 0}


def _save_state(state: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _next_id(state: dict) -> str:
    state["counter"] = state.get("counter", 0) + 1
    return f"EA{state['counter']:03d}"


def save_pending_approval(msg_id: str, email_data: dict, category: str) -> str:
    """Store an email pending user approval. Returns the approval_id (e.g. EA001)."""
    state = _load_state()
    _cleanup_expired(state)

    approval_id = _next_id(state)
    now = datetime.now(timezone.utc)
    state["pending"].append({
        "approval_id": approval_id,
        "msg_id": msg_id,
        "from": email_data.get("from", ""),
        "subject": email_data.get("subject", ""),
        "category": category,
        "snippet": email_data.get("snippet", "")[:400],
        "thread_id": email_data.get("thread_id", ""),
        "internet_message_id": email_data.get("internet_message_id", ""),
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=_APPROVAL_TTL_HOURS)).isoformat(),
    })
    _save_state(state)
    return approval_id


def find_pending(approval_id: str) -> Optional[dict]:
    """Look up a pending approval by ID. Returns None if not found or expired."""
    state = _load_state()
    now = datetime.now(timezone.utc)
    for entry in state["pending"]:
        if entry["approval_id"].upper() == approval_id.upper():
            expires = datetime.fromisoformat(entry["expires_at"])
            if now < expires:
                return entry
    return None


def remove_pending(approval_id: str):
    """Remove a pending approval (after accept or reject)."""
    state = _load_state()
    state["pending"] = [
        e for e in state["pending"]
        if e["approval_id"].upper() != approval_id.upper()
    ]
    _save_state(state)


def process_approval(approval_id: str, accepted: bool, task_dir: Path) -> str:
    """
    Handle ACCEPT or REJECT for an email approval.
    Returns a confirmation message to send back to the user via WhatsApp.
    """
    entry = find_pending(approval_id)
    if entry is None:
        return f"⚠️ Approval *{approval_id}* not found or already expired."

    remove_pending(approval_id)

    if not accepted:
        return f"❌ *{approval_id}* rejected — email from {entry['from']} will be skipped."

    # Accepted → create executor task
    try:
        from backend.src.models.task import TaskCreate, TaskSource, TaskType, TaskPriority
        from backend.src.services.task_writer import write_task_file

        category = entry["category"]
        cat_labels = {"linkedin": "LinkedIn", "bank": "Bank Statement", "indeed": "Indeed Job Alert"}
        label = cat_labels.get(category, category.title())

        type_map = {
            "linkedin": TaskType.GENERAL,
            "bank": TaskType.GENERAL,
            "indeed": TaskType.GENERAL,
        }
        task_type = type_map.get(category, TaskType.GENERAL)

        instruction_map = {
            "linkedin": f"Summarise this LinkedIn notification and suggest any action needed. From: {entry['from']} | Subject: {entry['subject']}",
            "bank": f"Analyse this bank statement/transaction email and summarise key financial activity. From: {entry['from']} | Subject: {entry['subject']}",
            "indeed": f"Summarise these job opportunities from Indeed and highlight the best matches. From: {entry['from']} | Subject: {entry['subject']}",
        }
        instruction = instruction_map.get(category, f"Process email: {entry['subject']}")

        create_data = TaskCreate(
            type=task_type,
            priority=TaskPriority.HIGH,
            source=TaskSource.GMAIL,
            instruction=instruction,
            context=(
                f"Category: {label}\n"
                f"From: {entry['from']}\n"
                f"Subject: {entry['subject']}\n"
                f"Thread-ID: {entry['thread_id']}\n"
                f"Message-ID: {entry['internet_message_id']}\n\n"
                f"{entry['snippet']}"
            ),
            source_ref=entry.get("internet_message_id") or entry["msg_id"],
        )
        task_id, _ = write_task_file(create_data, task_dir, auto_approve=True)
        print(f"[email_approval] Task created: {task_id} for approval {approval_id}")
        return (
            f"✅ *{approval_id}* accepted!\n"
            f"Task *{task_id}* created — the agent will process and summarise this {label} email."
        )
    except Exception as e:
        print(f"[email_approval] Task creation error: {e}")
        return f"✅ *{approval_id}* accepted but task creation failed: {e}"


def _cleanup_expired(state: dict):
    """Remove expired entries from the pending list."""
    now = datetime.now(timezone.utc)
    state["pending"] = [
        e for e in state["pending"]
        if datetime.fromisoformat(e["expires_at"]) > now
    ]
