"""Gmail API service — shared wrapper with auto-refresh for OAuth2 tokens."""

import base64
import json
import os
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_PATH = Path(os.getenv("MEMORY_DIR", "./memory")) / "gmail_token.json"


def _get_credentials() -> Optional[Credentials]:
    """Load credentials from token file, auto-refresh if expired."""
    if not TOKEN_PATH.exists():
        return None

    data = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
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
        TOKEN_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

    return creds


def _get_service():
    """Build and return Gmail API service object."""
    creds = _get_credentials()
    if creds is None:
        raise RuntimeError("Gmail not configured — run scripts/gmail_oauth_setup.py first")
    return build("gmail", "v1", credentials=creds)


def list_unread_emails(max_results: int = 10) -> list[dict]:
    """List unread emails from inbox. Returns list of {id, threadId}."""
    service = _get_service()
    results = service.users().messages().list(
        userId="me",
        q="is:unread is:inbox",
        maxResults=max_results,
    ).execute()
    return results.get("messages", [])


def get_email(msg_id: str) -> dict:
    """Fetch full email by message ID. Returns parsed dict."""
    service = _get_service()
    msg = service.users().messages().get(
        userId="me", id=msg_id, format="full"
    ).execute()

    headers = {
        h["name"].lower(): h["value"]
        for h in msg.get("payload", {}).get("headers", [])
    }

    body = _extract_body(msg.get("payload", {}))

    return {
        "message_id": msg.get("id"),
        "thread_id": msg.get("threadId"),
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "body": body,
        "internet_message_id": headers.get("message-id", ""),
    }


def _extract_body(payload: dict) -> str:
    """Recursively extract plain text body from Gmail payload."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        text = _extract_body(part)
        if text:
            return text
    return ""


def send_email(
    to: str,
    subject: str,
    body: str,
    reply_to_message_id: str = "",
    thread_id: str = "",
) -> dict:
    """Send an email via Gmail API. Returns {id, threadId, labelIds}."""
    service = _get_service()
    sender = os.getenv("GMAIL_MONITORED_EMAIL", "me")

    msg = MIMEText(body)
    msg["to"] = to
    msg["from"] = sender
    msg["subject"] = subject

    if reply_to_message_id:
        msg["In-Reply-To"] = reply_to_message_id
        msg["References"] = reply_to_message_id

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    send_body: dict = {"raw": raw}
    if thread_id:
        send_body["threadId"] = thread_id

    result = service.users().messages().send(
        userId="me", body=send_body
    ).execute()

    return {
        "id": result.get("id"),
        "threadId": result.get("threadId"),
        "labelIds": result.get("labelIds", []),
    }


def mark_as_read(msg_id: str) -> dict:
    """Remove UNREAD label from a message."""
    service = _get_service()
    result = service.users().messages().modify(
        userId="me",
        id=msg_id,
        body={"removeLabelIds": ["UNREAD"]},
    ).execute()
    return {"id": result.get("id"), "labelIds": result.get("labelIds", [])}
