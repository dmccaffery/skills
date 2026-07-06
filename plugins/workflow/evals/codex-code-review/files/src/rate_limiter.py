"""Sliding-window rate limiter."""

import time


class RateLimiter:
    """Allow at most ``limit`` calls per ``window`` seconds."""

    def __init__(self, limit: int, window: float) -> None:
        if limit <= 0:
            raise ValueError("limit must be positive")
        self.limit = limit
        self.window = window
        self._calls: list[float] = []

    def allow(self) -> bool:
        """Record an attempt and return whether it is within the limit."""
        now = time.monotonic()
        cutoff = now - self.window
        self._calls = [t for t in self._calls if t > cutoff]
        if len(self._calls) > self.limit:
            return False
        self._calls.append(now)
        return True
