"""T057: MCP email_send tool — send email via Gmail API with OAuth2."""

import sys
import time
from pathlib import Path

# Ensure project root is on path for gmail_service import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from mcp_server.src.logger import MCPLogger

logger = MCPLogger()


def email_send(
    to: str,
    subject: str,
    body: str,
    reply_to_message_id: str = "",
    thread_id: str = "",
    task_id: str = "unknown",
) -> dict:
    """Send an email via Gmail API with OAuth2."""
    start = time.time()

    try:
        from watchers.src.gmail_service import send_email

        api_result = send_email(
            to=to,
            subject=subject,
            body=body,
            reply_to_message_id=reply_to_message_id,
            thread_id=thread_id,
        )
        result = {
            "status": "sent",
            "message_id": api_result.get("id", ""),
            "thread_id": api_result.get("threadId", ""),
            "to": to,
            "subject": subject,
        }
        status = "success"
    except Exception as e:
        result = {"status": "error", "error": str(e)}
        status = "error"

    duration_ms = int((time.time() - start) * 1000)
    logger.log_invocation(
        task_id, "email_send",
        {"to": to, "subject": subject},
        result, status, duration_ms,
    )
    return result
