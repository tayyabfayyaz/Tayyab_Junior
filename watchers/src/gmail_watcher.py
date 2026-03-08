"""Gmail watcher — polls for emails from LinkedIn, Bank, and Indeed; sends WhatsApp approval requests."""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from watchers.src.base import BaseWatcher

# ── Platform detection rules ────────────────────────────────────────────────
_PLATFORM_RULES = {
    "linkedin": {
        "emoji": "💼",
        "from_domains": ["linkedin.com"],
        "from_keywords": [],
        "subject_keywords": [],
    },
    "bank": {
        "emoji": "🏦",
        "from_domains": [
            "mcb.com.pk", "hbl.com", "meezanbank.com", "ubldigital.com",
            "alfalabank.com", "habibbank.com", "bankislami.com.pk",
            "js.bank", "askari.com.pk", "standardchartered.com.pk",
        ],
        "from_keywords": ["bank", "statement", "noreply@", "alerts@"],
        "subject_keywords": [
            "statement", "transaction", "credit", "debit", "balance",
            "account", "payment", "transfer", "bank alert", "salary",
        ],
    },
    "indeed": {
        "emoji": "🔍",
        "from_domains": ["indeed.com"],
        "from_keywords": [],
        "subject_keywords": [],
    },
}


def _detect_platform(email_data: dict) -> str | None:
    """Return the platform key if the email matches a watched platform, else None."""
    from_addr = email_data.get("from", "").lower()
    subject = email_data.get("subject", "").lower()
    snippet = email_data.get("snippet", "").lower()

    for platform, rules in _PLATFORM_RULES.items():
        # Domain match in from address
        if any(domain in from_addr for domain in rules["from_domains"]):
            return platform
        # Keyword match in from address
        if rules["from_keywords"] and any(kw in from_addr for kw in rules["from_keywords"]):
            # Also check subject to avoid false positives for bank
            if platform == "bank" and any(kw in subject or kw in snippet for kw in rules["subject_keywords"]):
                return platform
    return None


class GmailWatcher(BaseWatcher):
    """Monitor Gmail for LinkedIn, Bank, and Indeed emails; request WhatsApp approval before processing."""

    def __init__(
        self,
        task_dir: str = "./tasks",
        log_dir: str = "./logs",
        credentials_path: str = "",
    ):
        super().__init__(name="gmail", poll_interval=300, log_dir=log_dir)
        self.task_dir = Path(task_dir)
        self.task_dir.mkdir(parents=True, exist_ok=True)
        self.credentials_path = credentials_path or str(
            Path(os.getenv("MEMORY_DIR", "./memory")) / "gmail_token.json"
        )
        self.state_path = Path(os.getenv("MEMORY_DIR", "./memory")) / "gmail_watcher_state.json"
        self.processed_ids: set[str] = self._load_processed_ids()

    # ── State persistence ───────────────────────────────────────────────────

    def _load_processed_ids(self) -> set[str]:
        if self.state_path.exists():
            try:
                return set(json.loads(self.state_path.read_text(encoding="utf-8")).get("processed_ids", []))
            except (json.JSONDecodeError, OSError):
                pass
        return set()

    def _save_processed_ids(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        recent = list(self.processed_ids)[-500:]
        self.state_path.write_text(json.dumps({"processed_ids": recent}), encoding="utf-8")

    # ── Gmail API helpers ───────────────────────────────────────────────────

    def _get_service(self):
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds_path = Path(self.credentials_path)
        if not creds_path.exists():
            raise RuntimeError(f"Gmail credentials not found at {creds_path}")

        data = json.loads(creds_path.read_text(encoding="utf-8"))
        creds = Credentials(
            token=data.get("token"),
            refresh_token=data.get("refresh_token"),
            token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=data.get("client_id", os.getenv("GMAIL_CLIENT_ID", "")),
            client_secret=data.get("client_secret", os.getenv("GMAIL_CLIENT_SECRET", "")),
            scopes=data.get("scopes"),
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            data["token"] = creds.token
            creds_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        return build("gmail", "v1", credentials=creds)

    def _get_full_message(self, service, msg_id: str) -> dict:
        msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        return {
            "id": msg.get("id"),
            "thread_id": msg.get("threadId"),
            "from": headers.get("From", "Unknown"),
            "subject": headers.get("Subject", "No Subject"),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
            "internet_message_id": headers.get("Message-ID", ""),
        }

    # ── Core polling loop ───────────────────────────────────────────────────

    async def poll(self):
        """Fetch unread emails; filter to LinkedIn/Bank/Indeed; request WhatsApp approval."""
        if not Path(self.credentials_path).exists():
            return

        try:
            service = self._get_service()
            results = service.users().messages().list(
                userId="me", q="is:unread", maxResults=25
            ).execute()
            all_msgs = results.get("messages", [])
            new_msgs = [m for m in all_msgs if m["id"] not in self.processed_ids]
            print(f"[gmail] Found {len(new_msgs)} unread email(s) to check")

            for msg_stub in new_msgs:
                msg_id = msg_stub["id"]
                email_data = self._get_full_message(service, msg_id)
                platform = _detect_platform(email_data)

                if platform is None:
                    print(f"[gmail] IGNORE | From: {email_data['from']} | Subject: {email_data['subject']}")
                    self.processed_ids.add(msg_id)
                    continue

                print(f"[gmail] {platform.upper()} | From: {email_data['from']} | Subject: {email_data['subject']}")

                self.log_event(
                    watcher_type="gmail",
                    raw_payload={
                        "from": email_data["from"],
                        "subject": email_data["subject"],
                        "platform": platform,
                    },
                    action_required=True,
                )

                # Send WhatsApp approval request (do NOT create task yet)
                self._request_whatsapp_approval(email_data, platform, msg_id)

                # Mark as processed so we don't send duplicate approval requests
                self.processed_ids.add(msg_id)

            self._save_processed_ids()

        except Exception as e:
            print(f"[gmail] Poll error: {e}")

    # ── WhatsApp approval request ───────────────────────────────────────────

    def _request_whatsapp_approval(self, email_data: dict, platform: str, msg_id: str):
        """Save pending approval and send WhatsApp notification asking for ACCEPT/REJECT."""
        try:
            from watchers.src.email_approval import save_pending_approval
            from executor.src.notifications import _send_whatsapp_direct

            owner = os.getenv("WHATSAPP_OWNER_PHONE", "")
            if not owner:
                print("[gmail] WhatsApp owner not configured — skipping approval request")
                return

            approval_id = save_pending_approval(msg_id, email_data, platform)

            rules = _PLATFORM_RULES[platform]
            emoji = rules["emoji"]

            # Truncate snippet for readability
            snippet = email_data.get("snippet", "")[:200]
            if len(email_data.get("snippet", "")) > 200:
                snippet += "..."

            msg = (
                f"{emoji} *Email Approval Needed*\n\n"
                f"*Platform:* {platform.title()}\n"
                f"*From:* {email_data['from']}\n"
                f"*Subject:* {email_data['subject']}\n\n"
                f"_{snippet}_\n\n"
                f"Reply to approve or reject:\n"
                f"✅ *ACCEPT {approval_id}*\n"
                f"❌ *REJECT {approval_id}*\n\n"
                f"_(Expires in 24 hours)_"
            )
            _send_whatsapp_direct(owner, msg)
            print(f"[gmail] Approval request sent | id={approval_id} | platform={platform}")

        except Exception as e:
            print(f"[gmail] WhatsApp approval request error: {e}")
