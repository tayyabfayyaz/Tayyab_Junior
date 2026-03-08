"""T046/T052: WhatsApp intent parser — extract task from natural language, handle ambiguity."""

import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def parse_whatsapp_message(message_text: str, sender_phone: str) -> Optional[dict]:
    """Use Gemini to extract task type, priority, instruction, context from WhatsApp message.
    Returns structured task data or None if ambiguous.
    """
    import json
    import re

    prompt = f"""You are a task extraction assistant. Parse the following WhatsApp message into a structured task.

Message from {sender_phone}: "{message_text}"

Extract and return a JSON object with these fields:
- "type": one of [email_reply, email_draft, social_post, social_reply, whatsapp_reply, coding_task, general]
  * Use "social_post" when the user wants to post/publish on LinkedIn, Twitter, Instagram, or any social media
  * Use "social_reply" when the user wants to reply/comment on a social media post
- "priority": one of [critical, high, medium, low]
- "instruction": clear instruction for the AI executor
- "context": relevant context from the message
- "constraints": any constraints mentioned (or null)
- "is_clear": true if the message contains a clear actionable instruction, false if ambiguous

Return ONLY valid JSON, no other text."""

    try:
        from google import genai as _genai
        client = _genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=prompt,
        )
        raw = response.text.strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        result = json.loads(raw)

        if not result.get("is_clear", True):
            return None

        return {
            "type": result.get("type", "general"),
            "priority": result.get("priority", "medium"),
            "instruction": result.get("instruction", message_text),
            "context": result.get("context", f"WhatsApp message from {sender_phone}"),
            "constraints": result.get("constraints"),
            "source": "whatsapp",
            "source_ref": sender_phone,
        }
    except Exception as e:
        print(f"[whatsapp_handler] Intent parse error: {e} — falling back to rule-based detection")

    # Rule-based fallback: detect social_post intent without AI
    lower = message_text.lower()
    social_keywords = ["post on", "publish on", "share on", "tweet", "post to linkedin",
                       "linkedin post", "twitter post", "post this", "write a post"]
    if any(kw in lower for kw in social_keywords):
        return {
            "type": "social_post",
            "priority": "medium",
            "instruction": f"Write and publish a social media post based on: {message_text}",
            "context": f"WhatsApp message from {sender_phone}",
            "constraints": None,
            "source": "whatsapp",
            "source_ref": sender_phone,
        }

    return {
        "type": "general",
        "priority": "medium",
        "instruction": message_text,
        "context": f"WhatsApp message from {sender_phone}",
        "constraints": None,
        "source": "whatsapp",
        "source_ref": sender_phone,
    }


def get_clarification_message() -> str:
    """Return a clarification request message for ambiguous WhatsApp commands."""
    return (
        "I couldn't understand your request clearly. "
        "Could you rephrase it with a specific action? For example:\n"
        "- 'Reply to Ali about pricing'\n"
        "- 'Draft a summary of today's meetings'\n"
        "- 'Post on LinkedIn about our new feature'"
    )
