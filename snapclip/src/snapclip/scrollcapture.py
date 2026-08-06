from __future__ import annotations

import time
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from snapclip.capture import ScreenCapture, unique_capture_path
from snapclip.config import Settings
from snapclip.markup import render_markup
from snapclip.queue import PasteQueue, QueueItem
from snapclip.stitch import stitch_vertical

Point = Tuple[int, int]
Rect = Tuple[int, int, int, int]

_MIN_REGION_SIZE = 10  # px; smaller than this is treated as an accidental click, not a drag


class ScrollCaptureState(Enum):
    IDLE = "idle"
    SELECTING_REGION = "selecting_region"
    CAPTURING = "capturing"


class ScrollCaptureSession:
    """Drives "hold hotkey -> drag out a region -> scroll to capture
    frames -> release hotkey to stitch+save" (see README's "Scroll
    capture" section). Each `on_*`/`start`/`finish` method corresponds
    to one real OS event; `hotkeys.py` wires the real global hotkey/
    mouse hooks to these calls, but the state machine itself takes no
    OS dependency, so it's fully unit-testable by calling these methods
    directly."""

    def __init__(
        self,
        capture: ScreenCapture,
        settings: Settings,
        queue: PasteQueue,
        stitch_fn: Callable[[List], object] = stitch_vertical,
        min_capture_interval: float = 0.15,
        now_fn: Callable[[], float] = time.monotonic,
    ):
        self._capture = capture
        self._settings = settings
        self._queue = queue
        self._stitch_fn = stitch_fn
        self._min_interval = min_capture_interval
        self._now_fn = now_fn

        self.state = ScrollCaptureState.IDLE
        self._region_start: Optional[Point] = None
        self._region: Optional[Rect] = None
        self._frames: list = []
        self._last_capture_time: Optional[float] = None

    def start(self) -> None:
        """Hotkey pressed down: begin region selection."""
        if self.state != ScrollCaptureState.IDLE:
            return
        self.state = ScrollCaptureState.SELECTING_REGION
        self._region_start = None
        self._region = None
        self._frames = []
        self._last_capture_time = None

    def on_mouse_down(self, point: Point) -> None:
        if self.state != ScrollCaptureState.SELECTING_REGION:
            return
        self._region_start = point

    def on_mouse_up(self, point: Point) -> None:
        """Mouse released while still holding the hotkey: the dragged
        rectangle becomes the capture region, and capturing starts
        immediately (this also captures the first frame)."""
        if self.state != ScrollCaptureState.SELECTING_REGION or self._region_start is None:
            return

        x0, y0 = self._region_start
        x1, y1 = point
        region: Rect = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
        self._region_start = None

        if region[2] - region[0] < _MIN_REGION_SIZE or region[3] - region[1] < _MIN_REGION_SIZE:
            return  # accidental click, not a real drag; stay in SELECTING_REGION and let the user retry

        self._region = region
        self.state = ScrollCaptureState.CAPTURING
        self._capture_frame()

    def on_scroll(self) -> None:
        """Mouse wheel moved while capturing. Debounced to at most one
        frame per `min_capture_interval` seconds even under rapid wheel
        events."""
        if self.state != ScrollCaptureState.CAPTURING:
            return
        now = self._now_fn()
        if self._last_capture_time is not None and (now - self._last_capture_time) < self._min_interval:
            return
        self._capture_frame(at=now)

    def finish(self) -> Optional[Path]:
        """Hotkey released: stitch and save whatever frames were
        captured. Returns the saved path, or None if the hotkey was
        released before a region was ever confirmed (nothing to save)."""
        had_frames = self.state == ScrollCaptureState.CAPTURING and bool(self._frames)
        self.state = ScrollCaptureState.IDLE

        if not had_frames:
            return None

        stitched = self._stitch_fn(self._frames)
        self._settings.img_dir.mkdir(parents=True, exist_ok=True)
        path = unique_capture_path(self._settings.img_dir, None)
        stitched.save(path)
        self._queue.push(QueueItem(kind="text", content=render_markup(self._settings.mode, path)))
        return path

    def _capture_frame(self, at: Optional[float] = None) -> None:
        image = self._capture.capture_region(self._region)
        self._frames.append(image)
        self._last_capture_time = at if at is not None else self._now_fn()
