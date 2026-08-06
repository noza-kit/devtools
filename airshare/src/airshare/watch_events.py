from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from airshare.watch_config import TEMP_SUFFIXES


class DebounceTracker:
    """Accumulates recently-changed file paths and, once no new event has
    arrived for a given path in `debounce_seconds`, hands it back as
    "settled" via `ready_batch()`. Files with a transfer-in-progress
    suffix (`.tmp`/`.part`/`.crdownload`) never enter the pending set at
    all, matching the spec's "final write completed" trigger without
    needing a filesystem-level close-on-write signal (which Windows'
    ReadDirectoryChangesW-based file watching doesn't expose the way
    Linux's inotify IN_CLOSE_WRITE does)."""

    def __init__(self, debounce_seconds: float, now_fn: Callable[[], float] = time.monotonic):
        self._debounce = debounce_seconds
        self._now = now_fn
        self._pending: dict[Path, float] = {}

    def notify_event(self, path: Path) -> None:
        if path.suffix.lower() in TEMP_SUFFIXES:
            return
        self._pending[path] = self._now()

    def ready_batch(self) -> list[Path]:
        """Call periodically. Returns (and removes from tracking) every
        pending path whose most recent event is at least
        `debounce_seconds` old."""
        now = self._now()
        ready = [path for path, last_event in self._pending.items() if now - last_event >= self._debounce]
        for path in ready:
            del self._pending[path]
        return ready

    def has_pending(self) -> bool:
        return bool(self._pending)

    def __len__(self) -> int:
        return len(self._pending)
