"""CEO Assistant — send daily report via Gmail (reuses watchers.src.gmail_service)."""

import sys
from pathlib import Path

from ceo_assistant.src.config import config


def send_report(report_path: Path) -> bool:
    """Send the report markdown file to CEO_EMAIL via Gmail.

    Returns True on success, False if skipped or failed.
    """
    if not config.ceo_email:
        print("[ceo-assistant] CEO_EMAIL not set — skipping email delivery.")
        return False

    try:
        from watchers.src.gmail_service import send_email
    except ImportError:
        print("[ceo-assistant] gmail_service unavailable — skipping email delivery.")
        return False

    try:
        content = report_path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"[ceo-assistant] Cannot read report file: {e}")
        return False

    # Derive subject from filename (YYYY-MM-DD.md)
    date_str = report_path.stem  # e.g. "2026-02-24"
    subject = f"CEO Daily Report — {date_str}"

    try:
        result = send_email(to=config.ceo_email, subject=subject, body=content)
        print(f"[ceo-assistant] Report emailed to {config.ceo_email} (msg id: {result.get('id')})")
        return True
    except Exception as e:
        print(f"[ceo-assistant] Email delivery failed: {e} — report saved at {report_path}")
        return False
