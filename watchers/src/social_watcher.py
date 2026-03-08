"""LinkedIn + Twitter social watcher — notifications, daily engagement, Twitter mentions."""

import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from watchers.src.base import BaseWatcher


class SocialWatcher(BaseWatcher):
    """Monitor LinkedIn and Twitter for comments, mentions, and daily engagement."""

    DAILY_LIKE_LIMIT = 10
    DAILY_COMMENT_LIMIT = 5

    def __init__(self, task_dir: str = "./tasks", log_dir: str = "./logs"):
        super().__init__(name="social", poll_interval=900, log_dir=log_dir)
        self.task_dir = Path(task_dir)
        self.memory_dir = Path(os.getenv("MEMORY_DIR", "./memory"))
        self.linkedin_token = self._load_linkedin_token()
        self._linkedin_scope: set[str] = self._load_linkedin_scope()
        self.twitter_api_key = os.getenv("TWITTER_API_KEY", "")
        self.twitter_api_secret = os.getenv("TWITTER_API_SECRET", "")
        self.twitter_access_token = os.getenv("TWITTER_ACCESS_TOKEN", "")
        self.twitter_access_secret = os.getenv("TWITTER_ACCESS_SECRET", "")
        self._person_urn: str | None = None
        self._seen_comment_ids: set[str] = self._load_seen_ids()
        self._twitter_user_id: str | None = None
        self._twitter_since_id: str | None = None
        self._load_twitter_state()

    # ── Token / scope loading ───────────────────────────────────────────────

    def _load_linkedin_token(self) -> str:
        token_path = self.memory_dir / "linkedin_token.json"
        if token_path.exists():
            try:
                return json.loads(token_path.read_text(encoding="utf-8")).get("access_token", "")
            except (json.JSONDecodeError, OSError):
                pass
        return os.getenv("LINKEDIN_ACCESS_TOKEN", "")

    def _load_linkedin_scope(self) -> set[str]:
        token_path = self.memory_dir / "linkedin_token.json"
        if token_path.exists():
            try:
                raw = json.loads(token_path.read_text(encoding="utf-8")).get("scope", "")
                return set(raw.split(","))
            except (json.JSONDecodeError, OSError):
                pass
        return set()

    # ── State persistence ───────────────────────────────────────────────────

    def _load_seen_ids(self) -> set[str]:
        state_path = self.memory_dir / "linkedin_watcher_state.json"
        if state_path.exists():
            try:
                return set(json.loads(state_path.read_text(encoding="utf-8")).get("seen_comment_ids", []))
            except (json.JSONDecodeError, OSError):
                pass
        return set()

    def _save_seen_ids(self):
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        state_path = self.memory_dir / "linkedin_watcher_state.json"
        state_path.write_text(
            json.dumps({"seen_comment_ids": list(self._seen_comment_ids)[-500:]}),
            encoding="utf-8",
        )

    def _load_known_connections(self) -> list[str]:
        path = self.memory_dir / "linkedin_known_connections.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8")).get("person_urns", [])
            except (json.JSONDecodeError, OSError):
                pass
        return []

    def _add_known_connection(self, person_urn: str):
        if not person_urn or not person_urn.startswith("urn:li:person:"):
            return
        connections = self._load_known_connections()
        if person_urn not in connections:
            connections.append(person_urn)
            connections = connections[-200:]  # keep last 200
            self.memory_dir.mkdir(parents=True, exist_ok=True)
            (self.memory_dir / "linkedin_known_connections.json").write_text(
                json.dumps({"person_urns": connections}), encoding="utf-8"
            )

    def _load_engagement_state(self) -> dict:
        path = self.memory_dir / "linkedin_engagement_state.json"
        today = date.today().isoformat()
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("date") == today:
                    return data
            except (json.JSONDecodeError, OSError):
                pass
        return {"date": today, "liked_posts": [], "commented_posts": []}

    def _save_engagement_state(self, state: dict):
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        (self.memory_dir / "linkedin_engagement_state.json").write_text(
            json.dumps(state), encoding="utf-8"
        )

    def _load_twitter_state(self):
        path = self.memory_dir / "twitter_watcher_state.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self._twitter_user_id = data.get("user_id")
                self._twitter_since_id = data.get("since_id")
            except (json.JSONDecodeError, OSError):
                pass

    def _save_twitter_state(self):
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        (self.memory_dir / "twitter_watcher_state.json").write_text(
            json.dumps({"user_id": self._twitter_user_id, "since_id": self._twitter_since_id}),
            encoding="utf-8",
        )

    # ── Poll dispatch ───────────────────────────────────────────────────────

    async def poll(self):
        if self.linkedin_token:
            await self._poll_linkedin_notifications()
            await self._poll_linkedin_daily_engagement()
        if self.twitter_api_key:
            await self._poll_twitter()

    # ── LinkedIn: resolve person URN (cached) ───────────────────────────────

    async def _resolve_person_urn(self, client, headers: dict) -> bool:
        if self._person_urn:
            return True
        import re as _re
        r = await client.get("https://api.linkedin.com/v2/userinfo", headers=headers)
        if r.status_code != 200:
            return False
        sub = r.json().get("sub", "")
        m = _re.search(r":(\d+)$", sub)
        numeric_id = m.group(1) if m else sub
        self._person_urn = f"urn:li:person:{numeric_id}"
        print(f"[social] LinkedIn person URN: {self._person_urn}")
        return True

    # ── LinkedIn: notifications (comments on own posts) ─────────────────────

    async def _poll_linkedin_notifications(self):
        """Check for new comments on own posts; auto-create reply tasks."""
        try:
            import httpx
            headers = {
                "Authorization": f"Bearer {self.linkedin_token}",
                "Content-Type": "application/json",
            }
            async with httpx.AsyncClient(timeout=30) as client:
                if not await self._resolve_person_urn(client, headers):
                    return

                # Fetch recent posts by user
                r = await client.get(
                    "https://api.linkedin.com/v2/ugcPosts",
                    headers=headers,
                    params={"q": "authors", "authors": f"List({self._person_urn})", "count": 10},
                )
                posts = r.json().get("elements", []) if r.status_code == 200 else []

                new_tasks = 0
                for post in posts:
                    post_urn = post.get("id", "")
                    if not post_urn:
                        continue

                    post_text = (
                        post.get("specificContent", {})
                        .get("com.linkedin.ugc.ShareContent", {})
                        .get("shareCommentary", {})
                        .get("text", "")
                    )

                    r = await client.get(
                        f"https://api.linkedin.com/v2/socialActions/{post_urn}/comments",
                        headers=headers,
                        params={"count": 20},
                    )
                    if r.status_code != 200:
                        continue

                    for comment in r.json().get("elements", []):
                        cid = comment.get("id", "")
                        if not cid or cid in self._seen_comment_ids:
                            continue

                        comment_text = comment.get("message", {}).get("text", "")
                        commenter_urn = comment.get("actor", "")

                        # Store commenter for daily engagement feature
                        self._add_known_connection(commenter_urn)

                        await self._create_auto_reply_task(
                            platform="linkedin",
                            source_ref=cid,
                            instruction=f"Reply to this LinkedIn comment on your post: {comment_text}",
                            context=(
                                f"Platform: LinkedIn\n"
                                f"Your post: {post_text[:300]}\n"
                                f"Commenter URN: {commenter_urn}\n"
                                f"Their comment: {comment_text}"
                            ),
                            constraints=(
                                "Reply as a senior professional. Be concise (1-3 sentences), "
                                "warm, and insightful. Add value to the conversation. "
                                "Reference specifics from their comment. Never use generic "
                                "openers like 'Great comment!' or 'Thanks for sharing!'"
                            ),
                        )
                        self._seen_comment_ids.add(cid)
                        new_tasks += 1
                        print(f"[social] LinkedIn comment queued for auto-reply: {cid}")

                if new_tasks:
                    self._save_seen_ids()
                    print(f"[social] LinkedIn notifications: {new_tasks} comment(s) → auto-reply queued")
                else:
                    print("[social] LinkedIn notifications: no new comments")

        except Exception as e:
            print(f"[social] LinkedIn notifications error: {e}")

    # ── LinkedIn: daily engagement (like + comment on connection posts) ──────

    async def _poll_linkedin_daily_engagement(self):
        """Like and AI-comment on connections' recent posts (10 likes + 5 comments per day)."""
        state = self._load_engagement_state()
        liked_today = len(state["liked_posts"])
        commented_today = len(state["commented_posts"])

        if liked_today >= self.DAILY_LIKE_LIMIT and commented_today >= self.DAILY_COMMENT_LIMIT:
            print(f"[social] LinkedIn engagement: daily limits reached ({liked_today} likes, {commented_today} comments)")
            return

        known_urns = self._load_known_connections()
        if not known_urns:
            print("[social] LinkedIn engagement: no known connections yet — will populate as people comment on your posts")
            return

        try:
            import httpx
            headers = {
                "Authorization": f"Bearer {self.linkedin_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            }
            async with httpx.AsyncClient(timeout=30) as client:
                if not await self._resolve_person_urn(client, headers):
                    return

                engaged = 0
                # Check up to 20 known connections
                for person_urn in known_urns[:20]:
                    if liked_today >= self.DAILY_LIKE_LIMIT and commented_today >= self.DAILY_COMMENT_LIMIT:
                        break

                    # Get their recent posts
                    r = await client.get(
                        "https://api.linkedin.com/v2/ugcPosts",
                        headers=headers,
                        params={"q": "authors", "authors": f"List({person_urn})", "count": 3},
                    )
                    if r.status_code != 200:
                        continue

                    for post in r.json().get("elements", []):
                        post_urn = post.get("id", "")
                        if not post_urn:
                            continue
                        if post_urn in state["liked_posts"] and post_urn in state["commented_posts"]:
                            continue

                        post_text = (
                            post.get("specificContent", {})
                            .get("com.linkedin.ugc.ShareContent", {})
                            .get("shareCommentary", {})
                            .get("text", "")[:500]
                        )

                        # Like the post
                        if liked_today < self.DAILY_LIKE_LIMIT and post_urn not in state["liked_posts"]:
                            liked = await self._like_post(client, headers, post_urn)
                            if liked:
                                state["liked_posts"].append(post_urn)
                                liked_today += 1
                                engaged += 1

                        # Queue an AI-generated comment
                        if commented_today < self.DAILY_COMMENT_LIMIT and post_urn not in state["commented_posts"]:
                            await self._create_auto_reply_task(
                                platform="linkedin",
                                source_ref=post_urn,
                                instruction=(
                                    f"Write a thoughtful 1-2 sentence comment on this LinkedIn post "
                                    f"by a connection: {post_text}"
                                ),
                                context=(
                                    f"Platform: LinkedIn\n"
                                    f"Author URN: {person_urn}\n"
                                    f"Post content: {post_text}"
                                ),
                                constraints=(
                                    "1-2 sentences only. Sound genuine and human — like a senior "
                                    "professional leaving a thoughtful remark. Ask a relevant question "
                                    "or share a brief insight. Never start with 'Great post!', "
                                    "'Insightful!', or other generic openers."
                                ),
                                priority="low",
                            )
                            state["commented_posts"].append(post_urn)
                            commented_today += 1
                            engaged += 1

                self._save_engagement_state(state)
                print(f"[social] LinkedIn engagement: {liked_today} likes, {commented_today} comments today (added {engaged} this cycle)")

        except Exception as e:
            print(f"[social] LinkedIn daily engagement error: {e}")

    async def _like_post(self, client, headers: dict, post_urn: str) -> bool:
        """Like a LinkedIn post. Returns True on success."""
        try:
            encoded = post_urn.replace(":", "%3A").replace(",", "%2C")
            r = await client.post(
                f"https://api.linkedin.com/v2/socialActions/{encoded}/likes",
                headers=headers,
                json={"actor": self._person_urn},
            )
            if r.status_code in (200, 201, 204):
                print(f"[social] Liked: {post_urn}")
                return True
            print(f"[social] Like failed ({r.status_code}) for {post_urn}: {r.text[:100]}")
            return False
        except Exception as e:
            print(f"[social] Like error: {e}")
            return False

    # ── Task creation (auto-approved — bypasses manual approval queue) ───────

    async def _create_auto_reply_task(
        self,
        platform: str,
        source_ref: str,
        instruction: str,
        context: str,
        constraints: str,
        priority: str = "medium",
    ):
        from backend.src.models.task import TaskCreate, TaskSource, TaskType, TaskPriority
        from backend.src.services.task_writer import write_task_file

        source = TaskSource.LINKEDIN if platform == "linkedin" else TaskSource.TWITTER
        prio_map = {"critical": TaskPriority.CRITICAL, "high": TaskPriority.HIGH,
                    "medium": TaskPriority.MEDIUM, "low": TaskPriority.LOW}

        create_data = TaskCreate(
            type=TaskType.SOCIAL_REPLY,
            priority=prio_map.get(priority, TaskPriority.MEDIUM),
            source=source,
            instruction=instruction,
            context=context,
            constraints=constraints,
            source_ref=source_ref,
        )
        task_id, _ = write_task_file(create_data, self.task_dir, auto_approve=True)
        self.log_event(
            watcher_type=f"linkedin_{platform}",
            raw_payload={"source_ref": source_ref, "instruction": instruction[:80]},
            action_required=True,
            task_id=task_id,
        )
        return task_id

    # ── Twitter polling ─────────────────────────────────────────────────────

    async def _poll_twitter(self):
        """Check Twitter/X for new mentions using API v2 with OAuth1."""
        try:
            from requests_oauthlib import OAuth1Session

            oauth = OAuth1Session(
                client_key=self.twitter_api_key,
                client_secret=self.twitter_api_secret,
                resource_owner_key=self.twitter_access_token,
                resource_owner_secret=self.twitter_access_secret,
            )

            if not self._twitter_user_id:
                r = oauth.get("https://api.twitter.com/2/users/me")
                r.raise_for_status()
                self._twitter_user_id = str(r.json()["data"]["id"])
                self._save_twitter_state()
                print(f"[social] Twitter user ID resolved: {self._twitter_user_id}")

            params: dict = {
                "max_results": 10,
                "tweet.fields": "author_id,text,created_at,conversation_id",
            }
            if self._twitter_since_id:
                params["since_id"] = self._twitter_since_id

            r = oauth.get(
                f"https://api.twitter.com/2/users/{self._twitter_user_id}/mentions",
                params=params,
            )
            if r.status_code != 200:
                print(f"[social] Twitter mentions error: {r.status_code}")
                return

            tweets = r.json().get("data", [])
            if not tweets:
                print("[social] Twitter: no new mentions")
                return

            new_tasks = 0
            for tweet in tweets:
                tweet_id = str(tweet["id"])
                await self._create_auto_reply_task(
                    platform="twitter",
                    source_ref=tweet_id,
                    instruction=f"Reply to this Twitter mention: {tweet['text']}",
                    context=(
                        f"Platform: Twitter/X\n"
                        f"Tweet ID: {tweet_id}\n"
                        f"Author ID: {tweet.get('author_id', 'unknown')}\n"
                        f"Tweet: {tweet['text']}"
                    ),
                    constraints=(
                        "Reply as a senior professional. Concise (max 240 chars). "
                        "Friendly, relevant, adds value."
                    ),
                )
                new_tasks += 1

            self._twitter_since_id = str(tweets[0]["id"])
            self._save_twitter_state()
            print(f"[social] Twitter: {new_tasks} mention(s) queued")

        except Exception as e:
            print(f"[social] Twitter poll error: {e}")
