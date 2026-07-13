from __future__ import annotations

import time
from threading import Lock
from typing import Optional


class Throttle:
    def __init__(self, delay_seconds: float) -> None:
        self._delay = max(delay_seconds, 0.0)
        self._lock = Lock()
        self._last_request_at: float = 0.0

    def wait(self, now: Optional[float] = None) -> None:
        if self._delay <= 0:
            return
        current = now if now is not None else time.time()
        with self._lock:
            elapsed = current - self._last_request_at
            if elapsed < self._delay:
                time.sleep(self._delay - elapsed)
            self._last_request_at = time.time()
