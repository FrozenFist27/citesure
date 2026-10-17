"""In-memory per-IP hourly rate limit and global daily cap (demo cost control)."""

from __future__ import annotations

import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, per_ip_per_hour: int, daily_cap: int, clock=time.time):
        self.per_ip = per_ip_per_hour
        self.daily_cap = daily_cap
        self.clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._day: int = -1
        self._day_count = 0

    def check(self, ip: str) -> str | None:
        """Record a request. Returns None if allowed, else 'ip' or 'daily' (the reason)."""
        now = self.clock()
        day = int(now // 86400)
        if day != self._day:
            self._day, self._day_count = day, 0
        if self._day_count >= self.daily_cap:
            return "daily"
        q = self._hits[ip]
        while q and now - q[0] > 3600:
            q.popleft()
        if len(q) >= self.per_ip:
            return "ip"
        q.append(now)
        self._day_count += 1
        return None
