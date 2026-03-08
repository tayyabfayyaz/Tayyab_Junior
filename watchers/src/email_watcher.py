"""T055: Email watcher — Gmail API with OAuth2, classify emails, create task files."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from watchers.src.base import BaseWatcher


class EmailWatcher(BaseWatcher):
    """Monitor Gmail inbox, classify emails, create tasks for action-required ones."""

    def __init__(self, task_dir: str = "./tasks", log_dir: str = "./logs"):
        super().__init__(name="email", poll_interval=120, log_dir=log_dir)
        self.task_dir = Path(task_dir)
        self.gmail_client_id = os.getenv("GMAIL_CLIENT_ID", "")
        self.gmail_client_secret = os.getenv("GMAIL_CLIENT_SECRET", "")
        self.state_path = Path(os.getenv("MEMORY_DIR", "./memory")) / "gmail_state.json"
        self.seen_ids: set[str] = self._load_seen_ids()

    def _load_seen_ids(self) -> set[str]:
        """Load previously seen message IDs from state file."""
        if self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text(encoding="utf-8"))
                return set(data.get("seen_ids", []))
            except (json.JSONDecodeError, OSError):
                pass
        return set()

    def _save_seen_ids(self):
        """Persist seen message IDs to state file."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        # Keep only last 500 IDs to prevent unbounded growth
        recent = list(self.seen_ids)[-500:]
        self.state_path.write_text(
            json.dumps({"seen_ids": recent}), encoding="utf-8"
        )

    async def poll(self):
        """Poll Gmail for new messages and create tasks for action-required emails."""
        if not self.gmail_client_id:
            return  # Gmail not configured

        try:
            from watchers.src.gmail_service import list_unread_emails, get_email, mark_as_read

            unread = list_unread_emails(max_results=10)

            for msg_stub in unread:
                msg_id = msg_stub["id"]
                if msg_id in self.seen_ids:
                    continue

                email_data = get_email(msg_id)
                self.seen_ids.add(msg_id)

                await self.process_email(email_data)

                mark_as_read(msg_id)

            self._save_seen_ids()

        except Exception as e:
            print(f"[email] Poll error: {e}")

    async def process_email(self, email_data: dict):
        """Process a single email: classify and optionally create a task."""
        sender = email_data.get("from", "unknown")
        subject = email_data.get("subject", "")
        body = email_data.get("body", "")

        # Classify using Claude
        is_action_required = await self._classify_email(sender, subject, body)

        self.log_event(
            watcher_type="email",
            raw_payload={"from": sender, "subject": subject},
            action_required=is_action_required,
        )

        if not is_action_required:
            return None

        # Create task file
        from backend.src.models.task import TaskCreate, TaskSource, TaskType, TaskPriority
        from backend.src.services.task_writer import write_task_file

        thread_id = email_data.get("thread_id", "")
        internet_message_id = email_data.get("internet_message_id", "")

        create_data = TaskCreate(
            type=TaskType.EMAIL_REPLY,
            priority=TaskPriority.MEDIUM,
            source=TaskSource.GMAIL,
            instruction=f"Draft a professional reply to this email from {sender} about: {subject}",
            context=(
                f"From: {sender}\n"
                f"Subject: {subject}\n"
                f"Thread-ID: {thread_id}\n"
                f"Message-ID: {internet_message_id}\n"
                f"\n{body}"
            ),
            source_ref=email_data.get("message_id"),
        )
        task_id, _ = write_task_file(create_data, self.task_dir)
        return task_id

    async def _classify_email(self, sender: str, subject: str, body: str) -> bool:
        """Use Claude to classify an email as action-required or informational."""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
            message = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=100,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Classify this email as 'action_required' or 'informational'.\n"
                        f"From: {sender}\nSubject: {subject}\nBody preview: {body[:500]}\n\n"
                        f"Reply with ONLY one word: action_required or informational"
                    ),
                }],
            )
            return "action_required" in message.content[0].text.lower()
        except Exception:
            return False
