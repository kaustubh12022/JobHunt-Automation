"""
Asynchronous Rate Limiter for Standalone Evaluation Dashboard.

Enforces:
- Gemini: <= 15 RPM (min interval 4.0s)
- Groq:   <= 20 RPM (min interval 3.0s)
"""

import asyncio
import time
from typing import List, Optional


class AsyncRateLimiter:
    """
    Sliding-window and minimum-interval rate limiter.
    Ensures that calls stay strictly within RPM limits and guarantees
    a minimum spacing between requests to avoid burst rate-limit errors.
    """

    def __init__(self, rpm: float, min_interval: Optional[float] = None, name: str = "Limiter"):
        if rpm <= 0:
            raise ValueError("RPM must be greater than 0")
        self.rpm = float(rpm)
        self.min_interval = float(min_interval) if min_interval is not None else (60.0 / self.rpm)
        self.name = name
        self.timestamps: List[float] = []
        self._lock = asyncio.Lock()
        self._last_call_time: float = 0.0

    async def acquire(self) -> float:
        """
        Wait until a slot is available under both RPM and minimum spacing rules.
        Returns the seconds waited.
        """
        waited_total = 0.0
        async with self._lock:
            loop = asyncio.get_running_loop()
            now = loop.time()

            # Evict timestamps older than 60 seconds
            window_start = now - 60.0
            self.timestamps = [t for t in self.timestamps if t > window_start]

            # If RPM cap reached in the sliding 60s window, sleep until the oldest one expires
            if len(self.timestamps) >= self.rpm:
                wait_time = (self.timestamps[0] + 60.0) - now
                if wait_time > 0:
                    waited_total += wait_time
                    await asyncio.sleep(wait_time)
                    now = loop.time()
                    window_start = now - 60.0
                    self.timestamps = [t for t in self.timestamps if t > window_start]

            # Enforce minimum interval spacing between consecutive requests
            elapsed = now - self._last_call_time
            if elapsed < self.min_interval:
                wait_spacing = self.min_interval - elapsed
                waited_total += wait_spacing
                await asyncio.sleep(wait_spacing)
                now = loop.time()

            self._last_call_time = now
            self.timestamps.append(now)

        return waited_total
