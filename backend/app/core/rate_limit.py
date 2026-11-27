"""Small in-process sliding-window rate limiter for local demonstrations.

This intentionally avoids pretending to be a distributed production limiter. Use
an API gateway or shared Redis-backed limiter when running multiple workers/hosts.
"""
from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from typing import Iterable

from starlette.responses import JSONResponse


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: int = 60):
        if limit < 1 or window_seconds < 1:
            raise ValueError("limit and window_seconds must be positive")
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        current = monotonic() if now is None else now
        cutoff = current - self.window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(current)
            return True


class RateLimitMiddleware:
    def __init__(
        self,
        app,
        requests_per_minute: int = 120,
        excluded_paths: Iterable[str] = (),
    ):
        self.app = app
        self.limiter = SlidingWindowLimiter(requests_per_minute, 60)
        self.excluded_paths = set(excluded_paths)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") in self.excluded_paths:
            await self.app(scope, receive, send)
            return
        client = scope.get("client")
        # Use the socket peer address only; do not trust caller-supplied forwarding headers.
        client_key = str(client[0]) if client else "unknown-client"
        if not self.limiter.allow(client_key):
            response = JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again shortly."},
                headers={"Retry-After": "60"},
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
