"""T074: Rate limiting middleware — configurable per-endpoint rate limits."""

import time
from collections import defaultdict

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter using sliding window."""

    def __init__(self, app, default_limit: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

        # Per-path rate limits (more restrictive for webhooks)
        self.path_limits: dict[str, int] = {
            "/api/v1/webhooks/": 30,
            "/api/v1/auth/login": 10,
        }

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        key = f"{client_ip}:{path}"

        # Determine limit for this path
        limit = self.default_limit
        for prefix, path_limit in self.path_limits.items():
            if path.startswith(prefix):
                limit = path_limit
                break

        now = time.time()
        window_start = now - self.window_seconds

        # Clean old entries and check count
        self._requests[key] = [t for t in self._requests[key] if t > window_start]

        if len(self._requests[key]) >= limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        self._requests[key].append(now)
        response = await call_next(request)
        return response
