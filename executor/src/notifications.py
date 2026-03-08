"""T050: Notification service — send completion/failure notifications via WhatsApp and Email."""

import json
import os
import re
import socket
from pathlib import Path
from typing import Optional

import yaml


def _call_mcp_tool(tool_name: str, task_id: str, params: dict) -> Optional[dict]:
    """Send a tool invocation to the MCP server via TCP socket."""
    mcp_url = os.getenv("MCP_SERVER_URL", "http://mcp-server:8001")
    try:
        parts = mcp_url.replace("http://", "").split(":")
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 8001

        request = json.dumps({
            "tool": tool_name,
            "task_id": task_id,
            "params": params,
        })

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(30)
            s.connect((host, port))
            s.sendall(request.encode("utf-8"))
            response = s.recv(65536)
        return json.loads(response.decode("utf-8"))
    except Exception:
        return None


def send_task_notification(
    task_id: str,
    task_source: str,
    source_ref: Optional[str],
    success: bool,
    result_preview: str,
    task_type: str = "",
):
    """Notify the originator AND execute the task action (e.g. publish post, send email).
    These two concerns are independent — a WhatsApp-sourced social_post must both
    reply to the sender and publish to LinkedIn.
    """
    # Step 1: notify the originator
    if task_source == "whatsapp":
        _notify_whatsapp(task_id, source_ref, success, result_preview)
    elif task_source == "gmail":
        # Gmail notification already sends the email reply — nothing else to do.
        _notify_gmail(task_id, success, result_preview)
        return

    # Step 2: execute the task action (independent of which channel triggered it)
    if not success:
        return
    if task_type in ("email_draft", "email_reply"):
        _send_outbound_email(task_id, result_preview)
    elif task_type == "social_post":
        _publish_social_post(task_id, result_preview)
    elif task_type == "social_reply":
        _publish_social_reply(task_id, result_preview)


def _send_whatsapp_direct(to: str, message: str, task_id: str = "unknown") -> bool:
    """Send a WhatsApp message directly via Business API (no MCP server required)."""
    import httpx

    access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    phone_id = os.getenv("WHATSAPP_PHONE_ID", "")
    if not access_token or not phone_id:
        print(f"[notifications] WhatsApp credentials not configured — skipping send to {to}")
        return False

    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }
    try:
        with httpx.Client(timeout=30) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
        msg_id = r.json().get("messages", [{}])[0].get("id", "unknown")
        print(f"[notifications] WhatsApp sent directly | to={to} | msg_id={msg_id} | task={task_id}")
        return True
    except Exception as e:
        print(f"[notifications] WhatsApp direct send failed: {e}")
        return False


def _notify_whatsapp(task_id: str, source_ref: Optional[str], success: bool, result_preview: str):
    """Send WhatsApp reply to the original sender, or notification to owner as fallback."""
    # If source_ref is the sender's phone, reply directly to them with the AI result
    recipient = source_ref if source_ref else os.getenv("WHATSAPP_OWNER_PHONE", "")
    if not recipient:
        return

    if success and source_ref:
        # Reply to the original sender with just the AI-generated result
        message = result_preview[:1000]
    elif success:
        message = f"Task {task_id} completed successfully.\n\nResult:\n{result_preview[:500]}"
    else:
        message = f"Task {task_id} failed.\n\nError:\n{result_preview[:500]}"

    _send_whatsapp_direct(recipient, message, task_id)


def _notify_gmail(task_id: str, success: bool, result_preview: str):
    """Send email reply for Gmail-originated tasks."""
    if not success or not result_preview:
        return

    _send_email_reply_from_task(task_id, result_preview)


def _send_email_reply_from_task(task_id: str, reply_body: str):
    """Read the task file to extract email metadata, then send the reply directly via Gmail API."""
    task_dir = Path(os.getenv("TASK_DIR", "./tasks"))

    # Task may be in processing or done directory at this point
    task_file = None
    for subdir in ["processing", "done", "need_action"]:
        candidate = task_dir / subdir / f"{task_id}.md"
        if candidate.exists():
            task_file = candidate
            break

    if task_file is None:
        print(f"[notifications] Gmail reply skipped — task file not found for {task_id}")
        return

    content = task_file.read_text(encoding="utf-8")

    # Extract context section
    context_match = re.search(r"## Context\s*\n(.*?)(?=\n##\s|\Z)", content, re.DOTALL)
    if not context_match:
        print(f"[notifications] Gmail reply skipped — no Context section in {task_id}")
        return

    context = context_match.group(1)

    # Parse email metadata from context
    from_match = re.search(r"From:\s*(.+)", context)
    subject_match = re.search(r"Subject:\s*(.+)", context)
    thread_id_match = re.search(r"Thread-ID:\s*(.+)", context)
    message_id_match = re.search(r"Message-ID:\s*(.+)", context)

    if not from_match:
        print(f"[notifications] Gmail reply skipped — no From: field in context for {task_id}")
        return

    recipient = from_match.group(1).strip()
    # Strip display name if present, e.g. "Alice <alice@example.com>" → "alice@example.com"
    email_in_brackets = re.search(r"<([^>]+)>", recipient)
    if email_in_brackets:
        recipient = email_in_brackets.group(1).strip()

    original_subject = subject_match.group(1).strip() if subject_match else ""
    reply_subject = (
        f"Re: {original_subject}"
        if original_subject and not original_subject.lower().startswith("re:")
        else original_subject
    )

    reply_to_message_id = message_id_match.group(1).strip() if message_id_match else ""
    thread_id = thread_id_match.group(1).strip() if thread_id_match else ""

    # Fallback: use source_ref from YAML frontmatter as reply_to_message_id
    if not reply_to_message_id:
        fm_parts = content.split("---", 2)
        if len(fm_parts) >= 3:
            try:
                meta = yaml.safe_load(fm_parts[1]) or {}
                reply_to_message_id = meta.get("source_ref", "")
            except Exception:
                pass

    try:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
        from watchers.src.gmail_service import send_email

        result = send_email(
            to=recipient,
            subject=reply_subject,
            body=reply_body,
            reply_to_message_id=reply_to_message_id,
            thread_id=thread_id,
        )
        print(
            f"[notifications] Gmail reply sent | to={recipient} | "
            f"subject={reply_subject} | msg_id={result.get('id')} | task={task_id}"
        )
    except Exception as e:
        print(f"[notifications] Gmail reply failed for {task_id}: {e}")
        raise


def _send_outbound_email(task_id: str, ai_result: str):
    """Send an outbound email for email_draft/email_reply tasks using Gmail API directly."""
    task_dir = Path(os.getenv("TASK_DIR", "./tasks"))

    # Find the task file
    task_file = None
    for subdir in ["processing", "done", "need_action"]:
        candidate = task_dir / subdir / f"{task_id}.md"
        if candidate.exists():
            task_file = candidate
            break
    if task_file is None:
        return

    content = task_file.read_text(encoding="utf-8")

    # Extract instruction and context sections
    instruction_match = re.search(r"## Instruction\s*\n(.*?)(?=\n##\s|\Z)", content, re.DOTALL)
    context_match = re.search(r"## Context\s*\n(.*?)(?=\n##\s|\Z)", content, re.DOTALL)
    instruction = instruction_match.group(1).strip() if instruction_match else ""
    context = context_match.group(1).strip() if context_match else ""

    # Find recipient email address (instruction first, then context)
    email_pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    to_addr = ""
    for text in (instruction, context):
        m = re.search(email_pattern, text)
        if m:
            to_addr = m.group(0)
            break
    if not to_addr:
        return

    # Parse Subject and Body from AI-generated result
    # Expected format: "Subject: ...\n\n<body>" or plain body
    subject = "Message from FTE Agent"
    body = ai_result.strip()

    subject_match = re.match(r"Subject:\s*(.+?)(?:\n|$)", ai_result, re.IGNORECASE)
    if subject_match:
        subject = subject_match.group(1).strip()
        body = ai_result[subject_match.end():].strip()
        # Strip leading blank lines or "Body:" label
        body = re.sub(r"^(Body:\s*\n?)?", "", body, flags=re.IGNORECASE).strip()

    try:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
        from watchers.src.gmail_service import send_email

        result = send_email(to=to_addr, subject=subject, body=body)
        print(f"[notifications] Email sent to {to_addr} | msg_id={result.get('id')} | subject={subject}")
    except Exception as e:
        print(f"[notifications] Email send failed: {e}")
        raise


def _resolve_task_file(task_id: str) -> Optional[Path]:
    """Find the task file across all status directories."""
    task_dir = Path(os.getenv("TASK_DIR", "./tasks"))
    for subdir in ["processing", "done", "need_action"]:
        candidate = task_dir / subdir / f"{task_id}.md"
        if candidate.exists():
            return candidate
    return None


def _extract_platform(content: str) -> str:
    """Detect platform (linkedin/twitter/facebook) from task content."""
    lower = content.lower()
    if "facebook" in lower or " fb " in lower:
        return "facebook"
    if "linkedin" in lower:
        return "linkedin"
    if "twitter" in lower or " x " in lower or "tweet" in lower:
        return "twitter"
    return "linkedin"  # default


_LINKEDIN_MAX_CHARS = 3000
_TWITTER_MAX_CHARS = 280
_FACEBOOK_MAX_CHARS = 63206

# Patterns the AI uses before the actual post content
_PREAMBLE_PATTERNS = [
    # "Here is/Here's a LinkedIn post ..." up through the first blank line(s)
    re.compile(
        r"^Here(?:'s| is)[^:\n]{0,80}:\s*\n+",
        re.IGNORECASE,
    ),
    # "Draft:", "Post:", "LinkedIn Post:", etc.
    re.compile(
        r"^(?:Draft|Post|LinkedIn\s+Post|Tweet|Social\s+Post):\s*\n+",
        re.IGNORECASE,
    ),
    # Leading markdown horizontal rule
    re.compile(r"^---+\s*\n"),
    # Leading image-placeholder lines like  **[Add an image ...]**
    re.compile(r"^\*\*\[[^\]]{0,200}\]\*\*\s*\n+"),
]


def _strip_preamble(text: str) -> str:
    """Remove AI preamble lines that precede the actual post."""
    for pattern in _PREAMBLE_PATTERNS:
        text = pattern.sub("", text)
    return text.strip()


def _strip_markdown(text: str) -> str:
    """Convert markdown to plain text suitable for social platforms."""
    # Image placeholder lines
    text = re.sub(r"\*\*\[[^\]]*\]\*\*\n?", "", text)
    # Horizontal rules → blank line
    text = re.sub(r"\n?---+\n?", "\n\n", text)
    # ATX headings → plain text
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Bold / italic
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*\n]+)\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"_([^_\n]+)_", r"\1", text)
    # Bullet list markers → bullet character
    text = re.sub(r"^\s*[\*\-]\s+", "• ", text, flags=re.MULTILINE)
    # Collapse 3+ blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _sanitize_post_content(ai_result: str, max_chars: int) -> str:
    """Strip AI preamble, markdown, and enforce platform character limit."""
    text = _strip_preamble(ai_result)
    text = _strip_markdown(text)
    if not text:
        # Fallback: use raw result stripped of only the most obvious preamble
        text = re.sub(r"^[^\n]*\n\n", "", ai_result.strip(), count=1)
    if len(text) > max_chars:
        text = text[: max_chars - 1] + "…"
    return text


def _publish_social_post(task_id: str, ai_result: str):
    """Publish the AI-generated post to LinkedIn or Twitter."""
    task_file = _resolve_task_file(task_id)
    if not task_file:
        raise RuntimeError(f"Task file not found for {task_id} — cannot publish post")

    content = task_file.read_text(encoding="utf-8")
    instruction_match = re.search(r"## Instruction\s*\n(.*?)(?=\n##\s|\Z)", content, re.DOTALL)
    instruction = instruction_match.group(1).strip() if instruction_match else ""

    platform = _extract_platform(instruction + content)
    max_chars = {
        "twitter": _TWITTER_MAX_CHARS,
        "facebook": _FACEBOOK_MAX_CHARS,
    }.get(platform, _LINKEDIN_MAX_CHARS)
    post_content = _sanitize_post_content(ai_result, max_chars)

    print(f"[notifications] Sanitized post ({len(post_content)} chars) for platform={platform}")

    if platform == "linkedin":
        _linkedin_post(task_id, post_content)
    elif platform == "twitter":
        _twitter_post(task_id, post_content)
    elif platform == "facebook":
        _facebook_post(task_id, post_content)


def _publish_social_reply(task_id: str, ai_result: str):
    """Post the AI-generated reply to LinkedIn or Twitter."""
    task_file = _resolve_task_file(task_id)
    if not task_file:
        raise RuntimeError(f"Task file not found for {task_id} — cannot publish reply")

    content = task_file.read_text(encoding="utf-8")
    instruction_match = re.search(r"## Instruction\s*\n(.*?)(?=\n##\s|\Z)", content, re.DOTALL)
    instruction = instruction_match.group(1).strip() if instruction_match else ""
    platform = _extract_platform(instruction + content)

    # source_ref holds the comment/tweet ID to reply to
    fm_parts = content.split("---", 2)
    reply_to_id = ""
    if len(fm_parts) >= 3:
        try:
            meta = yaml.safe_load(fm_parts[1]) or {}
            reply_to_id = meta.get("source_ref", "")
        except Exception:
            pass

    reply_content = ai_result.strip()

    if platform == "linkedin" and reply_to_id:
        _linkedin_reply(task_id, reply_to_id, reply_content)
    elif platform == "twitter" and reply_to_id:
        _twitter_reply(task_id, reply_to_id, reply_content)
    elif not reply_to_id:
        # No specific post to reply to — fall back to creating a new post
        _publish_social_post(task_id, ai_result)


def _get_linkedin_token() -> str:
    """Load LinkedIn token from memory file, fallback to env var."""
    import json as _json
    token_path = Path(os.getenv("MEMORY_DIR", "./memory")) / "linkedin_token.json"
    if token_path.exists():
        try:
            return _json.loads(token_path.read_text()).get("access_token", "")
        except Exception:
            pass
    return os.getenv("LINKEDIN_ACCESS_TOKEN", "")


def _extract_linkedin_member_id(sub: str) -> str:
    """Extract numeric member ID from a LinkedIn sub value.

    /v2/userinfo returns sub as either:
      - plain numeric string: "123456789"
      - URN:                  "urn:li:member:123456789" or "urn:li:person:123456789"
    UGC Posts author must be "urn:li:person:<numeric_id>".
    """
    import re
    m = re.search(r":(\d+)$", sub)
    return m.group(1) if m else sub


def _linkedin_post(task_id: str, post_content: str):
    """Post to LinkedIn UGC Posts API with correct person URN."""
    try:
        import httpx

        token = _get_linkedin_token()
        if not token:
            raise RuntimeError("LinkedIn access token not configured")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

        # Resolve person URN
        with httpx.Client(timeout=15) as client:
            r = client.get("https://api.linkedin.com/v2/userinfo", headers=headers)
            r.raise_for_status()
            sub = r.json().get("sub", "")

        if not sub:
            raise RuntimeError("Could not resolve LinkedIn person URN from /v2/userinfo")

        member_id = _extract_linkedin_member_id(sub)
        author_urn = f"urn:li:person:{member_id}"

        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": post_content},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }

        with httpx.Client(timeout=30) as client:
            resp = client.post(
                "https://api.linkedin.com/v2/ugcPosts",
                json=payload,
                headers=headers,
            )
            if not resp.is_success:
                print(f"[notifications] LinkedIn API error body: {resp.text}")
            resp.raise_for_status()
            post_id = resp.headers.get("x-linkedin-id") or resp.json().get("id", "unknown")
            print(f"[notifications] LinkedIn post published | author={author_urn} | post_id={post_id} | task={task_id}")

    except Exception as e:
        print(f"[notifications] LinkedIn post failed: {e}")
        raise


def _linkedin_reply(task_id: str, comment_id: str, reply_content: str):
    """Post a comment reply on LinkedIn."""
    try:
        import httpx

        token = _get_linkedin_token()
        if not token:
            raise RuntimeError("LinkedIn access token not configured")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

        with httpx.Client(timeout=15) as client:
            r = client.get("https://api.linkedin.com/v2/userinfo", headers=headers)
            r.raise_for_status()
            sub = r.json().get("sub", "")

        if not sub:
            raise RuntimeError("Could not resolve LinkedIn person URN from /v2/userinfo")

        member_id = _extract_linkedin_member_id(sub)

        payload = {
            "actor": f"urn:li:person:{member_id}",
            "message": {"text": reply_content},
        }

        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"https://api.linkedin.com/v2/socialActions/{comment_id}/comments",
                json=payload,
                headers=headers,
            )
            if not resp.is_success:
                print(f"[notifications] LinkedIn API error body: {resp.text}")
            resp.raise_for_status()
            print(f"[notifications] LinkedIn reply posted | comment_id={comment_id} | task={task_id}")

    except Exception as e:
        print(f"[notifications] LinkedIn reply failed: {e}")
        raise


def _facebook_post(task_id: str, post_content: str):
    """Publish a post to the configured Facebook Page."""
    try:
        import httpx

        page_token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "")
        page_id = os.getenv("FACEBOOK_PAGE_ID", "")
        if not page_token or not page_id:
            raise RuntimeError("FACEBOOK_PAGE_ACCESS_TOKEN or FACEBOOK_PAGE_ID not configured")

        url = f"https://graph.facebook.com/v22.0/{page_id}/feed"
        payload = {"message": post_content, "access_token": page_token}

        with httpx.Client(timeout=30) as client:
            resp = client.post(url, data=payload)
            if not resp.is_success:
                print(f"[notifications] Facebook API error: {resp.text}")
            resp.raise_for_status()
            post_id = resp.json().get("id", "unknown")
            print(f"[notifications] Facebook post published | page_id={page_id} | post_id={post_id} | task={task_id}")

    except Exception as e:
        print(f"[notifications] Facebook post failed: {e}")
        raise


def _twitter_post(task_id: str, post_content: str):
    """Post a tweet using OAuth1 (user-context)."""
    try:
        from requests_oauthlib import OAuth1Session

        oauth = OAuth1Session(
            client_key=os.getenv("TWITTER_API_KEY", ""),
            client_secret=os.getenv("TWITTER_API_SECRET", ""),
            resource_owner_key=os.getenv("TWITTER_ACCESS_TOKEN", ""),
            resource_owner_secret=os.getenv("TWITTER_ACCESS_SECRET", ""),
        )
        r = oauth.post(
            "https://api.twitter.com/2/tweets",
            json={"text": post_content},
        )
        r.raise_for_status()
        tweet_id = r.json().get("data", {}).get("id", "unknown")
        print(f"[notifications] Tweet posted | tweet_id={tweet_id} | task={task_id}")
    except Exception as e:
        print(f"[notifications] Twitter post failed: {e}")
        raise


def _twitter_reply(task_id: str, reply_to_id: str, reply_content: str):
    """Reply to a tweet using OAuth1."""
    try:
        from requests_oauthlib import OAuth1Session

        oauth = OAuth1Session(
            client_key=os.getenv("TWITTER_API_KEY", ""),
            client_secret=os.getenv("TWITTER_API_SECRET", ""),
            resource_owner_key=os.getenv("TWITTER_ACCESS_TOKEN", ""),
            resource_owner_secret=os.getenv("TWITTER_ACCESS_SECRET", ""),
        )
        r = oauth.post(
            "https://api.twitter.com/2/tweets",
            json={"text": reply_content, "reply": {"in_reply_to_tweet_id": reply_to_id}},
        )
        r.raise_for_status()
        tweet_id = r.json().get("data", {}).get("id", "unknown")
        print(f"[notifications] Twitter reply posted | tweet_id={tweet_id} | task={task_id}")
    except Exception as e:
        print(f"[notifications] Twitter reply failed: {e}")
        raise
