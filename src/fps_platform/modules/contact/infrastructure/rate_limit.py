from __future__ import annotations

from collections import defaultdict, deque
from math import ceil
from threading import Lock

from fps_platform.modules.contact.application.ports import ContactRateLimiter
from fps_platform.shared.domain.clock import Clock


class InMemoryContactRateLimiter(ContactRateLimiter):
    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._events: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def retry_after(self, client_ip: str, *, limit: int, window_seconds: int) -> int:
        moment = self._clock.now().timestamp()
        key = client_ip.strip() or "unknown"
        with self._lock:
            events = self._events[key]
            while events and events[0] <= moment - window_seconds:
                events.popleft()
            if len(events) >= limit:
                return max(1, ceil(events[0] + window_seconds - moment))
            events.append(moment)
            return 0
