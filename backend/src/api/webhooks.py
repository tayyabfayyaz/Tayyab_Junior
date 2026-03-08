"""T047/T048/T056/T078: Webhook router — WhatsApp, Email, GitHub webhook endpoints."""

import hashlib
import hmac
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response

from backend.src.config import settings
from backend.src.models.task import TaskCreate, TaskSource, TaskType, TaskPriority

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature for webhook payloads."""
    expected = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


# --- WhatsApp ---

@router.get("/whatsapp")
async def whatsapp_verify(request: Request):
    """Meta webhook verification challenge-response."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    """Receive WhatsApp messages, handle email approvals or parse intent into tasks."""
    import re as _re

    body = await request.body()

    # Verify signature using App Secret (not verify token)
    signature = request.headers.get("X-Hub-Signature-256", "")
    if settings.whatsapp_app_secret and signature:
        if not _verify_signature(body, signature, settings.whatsapp_app_secret):
            raise HTTPException(status_code=403, detail="Invalid signature")

    payload = json.loads(body)

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])
            if not messages:
                continue
            for msg in messages:
                sender = msg.get("from", "unknown")
                text = msg.get("text", {}).get("body", "").strip()
                if not text:
                    continue

                # ── Priority 1: On-demand daily report ──────────────────────
                _REPORT_KEYWORDS = (
                    "daily report", "send report", "send me report",
                    "generate report", "show report", "get report", "report"
                )
                if any(kw in text.lower() for kw in _REPORT_KEYWORDS):
                    from executor.src.notifications import _send_whatsapp_direct
                    try:
                        from ceo_assistant.src.report_generator import generate_report
                        from pathlib import Path as _Path
                        engine = request.app.state.task_engine
                        report_path = generate_report(task_dir=str(engine.task_dir))
                        content = _Path(report_path).read_text(encoding="utf-8")

                        # Strip YAML frontmatter and convert to WhatsApp-friendly text
                        parts = content.split("---", 2)
                        body = parts[2].strip() if len(parts) >= 3 else content

                        # Trim to WhatsApp limit (4096 chars)
                        if len(body) > 3800:
                            body = body[:3800] + "\n\n_(Report truncated — full report in email)_"

                        _send_whatsapp_direct(sender, body)
                    except Exception as _e:
                        _send_whatsapp_direct(sender, f"⚠️ Failed to generate report: {_e}")
                    continue

                # ── Priority 2: Email approval responses (ACCEPT/REJECT EAxxx) ──
                approval_match = _re.match(
                    r"^(ACCEPT|REJECT)\s+(EA\d+)$", text.upper()
                )
                if approval_match:
                    action = approval_match.group(1)   # "ACCEPT" or "REJECT"
                    approval_id = approval_match.group(2)  # e.g. "EA001"

                    from watchers.src.email_approval import process_approval
                    from executor.src.notifications import _send_whatsapp_direct

                    engine = request.app.state.task_engine
                    reply = process_approval(
                        approval_id=approval_id,
                        accepted=(action == "ACCEPT"),
                        task_dir=engine.task_dir,
                    )
                    _send_whatsapp_direct(sender, reply)
                    continue

                # ── Priority 2: General AI task (existing flow) ──────────────
                from watchers.src.whatsapp_handler import parse_whatsapp_message, get_clarification_message

                task_data = parse_whatsapp_message(text, sender)

                if task_data is None:
                    from executor.src.notifications import _send_whatsapp_direct
                    _send_whatsapp_direct(sender, get_clarification_message())
                    continue

                from backend.src.services.task_writer import write_task_file

                engine = request.app.state.task_engine
                create_data = TaskCreate(
                    type=TaskType(task_data["type"]),
                    priority=TaskPriority(task_data["priority"]),
                    source=TaskSource.WHATSAPP,
                    instruction=task_data["instruction"],
                    context=task_data["context"],
                    constraints=task_data.get("constraints"),
                    source_ref=task_data.get("source_ref"),
                )
                task_id, _ = write_task_file(create_data, engine.task_dir, auto_approve=True)
                engine._log_transition(task_id, "created", "need_action", actor="whatsapp_webhook")

    return {"status": "received"}


# --- Email (Gmail Pub/Sub) ---

@router.post("/email")
async def email_webhook(request: Request):
    """Receive Gmail push notification, trigger email watcher processing."""
    payload = await request.json()
    # Google Cloud Pub/Sub push notification
    message = payload.get("message", {})
    data = message.get("data", "")

    if data:
        import base64
        decoded = base64.b64decode(data).decode("utf-8")
        # Trigger email watcher to process the notification
        # In production, this would signal the email_watcher service
        # For now, log the event
        import json as json_mod
        from datetime import datetime, timezone

        event = {
            "event_id": message.get("messageId", "unknown"),
            "watcher_type": "email",
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "action_required": True,
            "raw_payload": decoded,
        }
        from pathlib import Path
        log_path = Path(settings.log_dir) / "watcher-events.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json_mod.dumps(event) + "\n")

    return {"status": "received"}


# --- GitHub ---

@router.post("/github")
async def github_webhook(request: Request):
    """Receive GitHub webhook events, create task files for actionable events."""
    body = await request.body()

    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    if settings.github_webhook_secret and signature:
        if not _verify_signature(body, signature, settings.github_webhook_secret):
            raise HTTPException(status_code=403, detail="Invalid signature")

    event_type = request.headers.get("X-GitHub-Event", "ping")
    payload = json.loads(body)

    actionable_events = ["issues", "pull_request", "pull_request_review"]
    if event_type not in actionable_events:
        return {"status": "received"}

    # Create task for actionable GitHub events
    from backend.src.services.task_writer import write_task_file

    engine = request.app.state.task_engine
    action = payload.get("action", "")
    repo = payload.get("repository", {}).get("full_name", "unknown")

    if event_type == "pull_request" and action in ("opened", "review_requested"):
        pr = payload.get("pull_request", {})
        create_data = TaskCreate(
            type=TaskType.CODING_TASK,
            priority=TaskPriority.HIGH,
            source=TaskSource.GITHUB,
            instruction=f"Review pull request #{pr.get('number')}: {pr.get('title')}",
            context=f"Repository: {repo}\nDescription: {pr.get('body', 'No description')}",
            source_ref=pr.get("html_url"),
        )
        task_id, _ = write_task_file(create_data, engine.task_dir)
        engine._log_transition(task_id, "created", "need_action", actor="github_webhook")

    elif event_type == "issues" and action in ("opened", "assigned"):
        issue = payload.get("issue", {})
        create_data = TaskCreate(
            type=TaskType.CODING_TASK,
            priority=TaskPriority.MEDIUM,
            source=TaskSource.GITHUB,
            instruction=f"Address issue #{issue.get('number')}: {issue.get('title')}",
            context=f"Repository: {repo}\nBody: {issue.get('body', 'No body')}",
            source_ref=issue.get("html_url"),
        )
        task_id, _ = write_task_file(create_data, engine.task_dir)
        engine._log_transition(task_id, "created", "need_action", actor="github_webhook")

    return {"status": "received"}
