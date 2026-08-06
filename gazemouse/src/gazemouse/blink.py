from __future__ import annotations

import math
import time
from typing import Callable, Sequence

from gazemouse.landmarks import LEFT_EYE_EAR_INDICES, RIGHT_EYE_EAR_INDICES, FaceLandmarks, Point

DEFAULT_EAR_THRESHOLD = 0.2
DEFAULT_HOLD_SECONDS = 2.0


def _dist(a: Point, b: Point) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def eye_aspect_ratio(points: Sequence[Point]) -> float:
    """The standard EAR formula (Soukupová & Čech, 2016):
    (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||), given the 6 eye-outline
    points in (outer_corner, upper_1, upper_2, inner_corner, lower_1,
    lower_2) order. A smaller EAR means a more-closed eye."""
    p1, p2, p3, p4, p5, p6 = points
    return (_dist(p2, p6) + _dist(p3, p5)) / (2 * _dist(p1, p4))


def face_ear(face: FaceLandmarks) -> float:
    """The minimum of the two eyes' EAR -- so either both eyes closing
    *or* a single deliberate wink (per the spec's "両目または片目")
    both count as "closed" for blink-hold detection."""
    left = eye_aspect_ratio([face.points[i] for i in LEFT_EYE_EAR_INDICES])
    right = eye_aspect_ratio([face.points[i] for i in RIGHT_EYE_EAR_INDICES])
    return min(left, right)


class BlinkDetector:
    """Fires exactly once per sustained closed-eye episode, the moment
    the eye(s) have been below `ear_threshold` for `hold_seconds`
    continuously -- not on every frame while still closed, and not at
    all for an ordinary physiological blink (typically 0.1-0.3s, far
    under the default 2s hold)."""

    def __init__(
        self,
        ear_threshold: float = DEFAULT_EAR_THRESHOLD,
        hold_seconds: float = DEFAULT_HOLD_SECONDS,
        now_fn: Callable[[], float] = time.monotonic,
    ):
        self.ear_threshold = ear_threshold
        self.hold_seconds = hold_seconds
        self._now = now_fn
        self._closed_since: float | None = None
        self._triggered = False

    def update(self, ear: float) -> bool:
        now = self._now()
        if ear < self.ear_threshold:
            if self._closed_since is None:
                self._closed_since = now
            if not self._triggered and now - self._closed_since >= self.hold_seconds:
                self._triggered = True
                return True
        else:
            self._closed_since = None
            self._triggered = False
        return False
