from __future__ import annotations

import math
from typing import Optional

from gazemouse.landmarks import FINGER_PIP_INDICES, FINGER_TIP_INDICES, WRIST_INDEX, HandLandmarks, Point

OPEN_FINGER_MAJORITY = 3  # of 4 tracked fingers (index/middle/ring/pinky)


def _dist(a: Point, b: Point) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def is_hand_open(hand: HandLandmarks) -> bool:
    """A finger counts as "extended" if its tip is farther from the
    wrist than its own PIP (middle) joint is -- true when straight,
    false when curled into a fist. "Open" (パー) is a majority (>=3 of
    4) of the tracked fingers extended; "closed" (グー) is not."""
    wrist = hand.points[WRIST_INDEX]
    extended = sum(
        1
        for tip_idx, pip_idx in zip(FINGER_TIP_INDICES, FINGER_PIP_INDICES)
        if _dist(wrist, hand.points[tip_idx]) > _dist(wrist, hand.points[pip_idx])
    )
    return extended >= OPEN_FINGER_MAJORITY


class ClickGestureDetector:
    """Maps the open<->closed hand transition directly onto
    mouse-button press/release (not a synthetic "click" event) -- an
    open->closed edge is "press", closed->open is "release". A quick
    press+release is an ordinary click; staying closed while the gaze
    cursor moves is, for free, a drag -- the same mechanism a physical
    mouse button uses, per the spec's own "長押し中はドラッグ＆ドロップ
    状態として扱う"."""

    def __init__(self):
        self._was_open = True

    def update(self, hand: Optional[HandLandmarks]) -> Optional[str]:
        """Returns "press", "release", or None (including every frame
        the state doesn't change, and every frame no hand is visible
        at all -- a missing hand is treated as "open"/neutral, not as
        a change in itself)."""
        is_open = is_hand_open(hand) if hand is not None else True
        event = None
        if self._was_open and not is_open:
            event = "press"
        elif not self._was_open and is_open:
            event = "release"
        self._was_open = is_open
        return event
