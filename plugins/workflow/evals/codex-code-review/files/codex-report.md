# Codex review report

Target: uncommitted changes (`src/rate_limiter.py`)

## Findings

### 1. Off-by-one in the rate-limit check (high)

`src/rate_limiter.py`, `RateLimiter.allow`: the guard `if len(self._calls) > self.limit` only rejects once the window
already holds **more than** `limit` calls, so every window admits `limit + 1` calls before the first `False` is
returned. A limiter configured for 100 requests per minute allows 101.

### 2. Unbounded memory growth in `_calls` (medium)

`src/rate_limiter.py`, `RateLimiter.allow`: timestamps are appended on every allowed call but never removed, so `_calls`
grows without bound in a long-running process and eventually exhausts memory.
