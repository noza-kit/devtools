from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RateMeter:
    """Rolling-window FPS from `tick()` call timestamps."""

    window: int = 30
    _timestamps: deque = field(default_factory=deque, repr=False)

    def tick(self) -> None:
        now = time.monotonic()
        self._timestamps.append(now)
        while len(self._timestamps) > self.window:
            self._timestamps.popleft()

    @property
    def fps(self) -> float:
        if len(self._timestamps) < 2:
            return 0.0
        span = self._timestamps[-1] - self._timestamps[0]
        if span <= 0:
            return 0.0
        return (len(self._timestamps) - 1) / span


@dataclass
class LatencyTracker:
    """Rolling-window latency between a sender timestamp (`time.time()` on
    the sending side) and when it's recorded here."""

    window: int = 30
    _samples: deque = field(default_factory=deque, repr=False)

    def record(self, sent_at: float) -> float:
        latency = time.time() - sent_at
        self._samples.append(latency)
        while len(self._samples) > self.window:
            self._samples.popleft()
        return latency

    @property
    def avg_ms(self) -> float:
        if not self._samples:
            return 0.0
        return sum(self._samples) / len(self._samples) * 1000


class MetricsLogger:
    """Tracks FPS + latency and logs them at a fixed interval."""

    def __init__(self, interval: float = 5.0):
        self.rate = RateMeter()
        self.latency = LatencyTracker()
        self.interval = interval
        self._last_log = time.monotonic()

    def record_frame(self, sent_at: float) -> None:
        self.rate.tick()
        self.latency.record(sent_at)
        now = time.monotonic()
        if now - self._last_log >= self.interval:
            logger.info("recv fps=%.1f avg_latency=%.1fms", self.rate.fps, self.latency.avg_ms)
            self._last_log = now
