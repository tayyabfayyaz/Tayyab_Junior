"""T062-T063: MCP social_post and social_reply tools."""

import os
import time

import httpx

from mcp_server.src.logger import MCPLogger

logger = MCPLogger()


def social_post(
    platform: str,
    content: str,
    media_urls: list[str] | None = None,
    task_id: str = "unknown",
) -> dict:
    """Publish a post to LinkedIn or Twitter."""
    start = time.time()

    try:
        if platform == "linkedin":
            result = _post_linkedin(content, media_urls or [])
        elif platform == "twitter":
            result = _post_twitter(content, media_urls or [])
        else:
            result = {"status": "error", "error": f"Unsupported platform: {platform}"}
        status = "success" if result.get("status") == "published" else "error"
    except Exception as e:
        result = {"status": "error", "error": str(e)}
        status = "error"

    duration_ms = int((time.time() - start) * 1000)
    logger.log_invocation(
        task_id, "social_post",
        {"platform": platform, "content": content[:100]},
        result, status, duration_ms,
    )
    return result


def social_reply(
    platform: str,
    reply_to_id: str,
    content: str,
    task_id: str = "unknown",
) -> dict:
    """Reply to a post on LinkedIn or Twitter."""
    start = time.time()

    try:
        if platform == "linkedin":
            result = _reply_linkedin(reply_to_id, content)
        elif platform == "twitter":
            result = _reply_twitter(reply_to_id, content)
        else:
            result = {"status": "error", "error": f"Unsupported platform: {platform}"}
        status = "success" if result.get("status") == "published" else "error"
    except Exception as e:
        result = {"status": "error", "error": str(e)}
        status = "error"

    duration_ms = int((time.time() - start) * 1000)
    logger.log_invocation(
        task_id, "social_reply",
        {"platform": platform, "reply_to_id": reply_to_id},
        result, status, duration_ms,
    )
    return result


def _load_linkedin_token() -> str:
    """Load LinkedIn token from file first, fallback to env var."""
    from pathlib import Path
    import json as _json
    token_path = Path(os.getenv("MEMORY_DIR", "./memory")) / "linkedin_token.json"
    if token_path.exists():
        try:
            return _json.loads(token_path.read_text()).get("access_token", "")
        except Exception:
            pass
    return os.getenv("LINKEDIN_ACCESS_TOKEN", "")


def _post_linkedin(content: str, media_urls: list[str]) -> dict:
    """Post to LinkedIn via Share API."""
    token = _load_linkedin_token()
    if not token:
        return {"status": "error", "error": "LinkedIn credentials not configured"}

    try:
        with httpx.Client() as client:
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            # Resolve actual person URN (urn:li:person:me is not valid)
            r = client.get("https://api.linkedin.com/v2/userinfo", headers=headers, timeout=15)
            r.raise_for_status()
            person_id = r.json().get("sub", "")
            if not person_id:
                return {"status": "error", "error": "Could not resolve LinkedIn person URN"}

            payload = {
                "author": f"urn:li:person:{person_id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": content},
                        "shareMediaCategory": "NONE",
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
            }
            resp = client.post("https://api.linkedin.com/v2/ugcPosts", json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            post_id = resp.headers.get("x-linkedin-id") or resp.json().get("id", "unknown")
            return {"status": "published", "post_id": post_id, "url": f"https://linkedin.com/feed/update/{post_id}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _post_twitter(content: str, media_urls: list[str]) -> dict:
    """Post to Twitter/X via API v2."""
    api_key = os.getenv("TWITTER_API_KEY", "")
    if not api_key:
        return {"status": "error", "error": "Twitter credentials not configured"}

    try:
        with httpx.Client() as client:
            bearer = os.getenv("TWITTER_ACCESS_TOKEN", "")
            headers = {"Authorization": f"Bearer {bearer}", "Content-Type": "application/json"}
            resp = client.post(
                "https://api.twitter.com/2/tweets",
                json={"text": content},
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            tweet_id = data.get("data", {}).get("id", "unknown")
            return {"status": "published", "post_id": tweet_id, "url": f"https://x.com/i/status/{tweet_id}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _reply_linkedin(reply_to_id: str, content: str) -> dict:
    """Reply to a LinkedIn post via socialActions comment API."""
    token = _load_linkedin_token()
    if not token:
        return {"status": "error", "error": "LinkedIn credentials not configured"}

    try:
        with httpx.Client() as client:
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            # Resolve person URN
            r = client.get("https://api.linkedin.com/v2/userinfo", headers=headers, timeout=15)
            person_urn = r.json().get("sub", "") if r.status_code == 200 else ""
            payload = {"actor": person_urn, "message": {"text": content}}
            resp = client.post(
                f"https://api.linkedin.com/v2/socialActions/{reply_to_id}/comments",
                json=payload,
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            reply_id = resp.headers.get("X-RestLi-Id", f"li-reply-{int(time.time())}")
            return {"status": "published", "reply_id": reply_id}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _reply_twitter(reply_to_id: str, content: str) -> dict:
    """Reply to a Twitter tweet."""
    bearer = os.getenv("TWITTER_ACCESS_TOKEN", "")
    if not bearer:
        return {"status": "error", "error": "Twitter credentials not configured"}

    try:
        with httpx.Client() as client:
            headers = {"Authorization": f"Bearer {bearer}", "Content-Type": "application/json"}
            resp = client.post(
                "https://api.twitter.com/2/tweets",
                json={"text": content, "reply": {"in_reply_to_tweet_id": reply_to_id}},
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return {"status": "published", "reply_id": data.get("data", {}).get("id", "unknown")}
    except Exception as e:
        return {"status": "error", "error": str(e)}
