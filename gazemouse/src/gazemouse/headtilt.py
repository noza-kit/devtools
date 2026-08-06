from __future__ import annotations

from typing import Optional

from gazemouse.landmarks import CHIN_INDEX, FOREHEAD_INDEX, FaceLandmarks

DEFAULT_DEADZONE = 0.02
DEFAULT_SCROLL_SCALE = 500.0


def estimate_pitch(face: FaceLandmarks) -> float:
    """A simple head-pitch proxy: the normalized-image-coordinate
    vertical distance between the chin and forehead landmarks. This
    grows as the head tilts down (chin drops away from the forehead in
    image-Y) and shrinks as it tilts up -- relative to a per-session
    baseline (see HeadTiltScroll), not an absolute angle in degrees,
    which is all scrolling actually needs. Chosen over MediaPipe Pose
    specifically so head-tilt scrolling doesn't need a third model
    loaded (Face Mesh landmarks alone are already loaded for gaze/blink)."""
    forehead = face.points[FOREHEAD_INDEX]
    chin = face.points[CHIN_INDEX]
    return chin.y - forehead.y


class HeadTiltScroll:
    """Converts head-pitch deviation from a calibrated baseline into a
    scroll delta. Deliberately a *separate* signal from gaze (which
    drives the cursor): tying scroll to gaze itself would mean looking
    down to scroll also drags the cursor down, the exact
    "コントロールとビューの競合" the spec calls out as the reason to use
    head tilt instead of gaze for scrolling."""

    def __init__(self, deadzone: float = DEFAULT_DEADZONE, scroll_scale: float = DEFAULT_SCROLL_SCALE):
        self.deadzone = deadzone
        self.scroll_scale = scroll_scale
        self._baseline: Optional[float] = None

    def calibrate_baseline(self, pitch: float) -> None:
        self._baseline = pitch

    def reset(self) -> None:
        self._baseline = None

    def scroll_delta(self, pitch: float) -> int:
        """Returns a signed scroll amount (positive = scroll up,
        negative = scroll down, matching most OS scroll-event
        conventions) for this frame's head pitch. The very first call
        (no baseline yet) calibrates silently and returns 0, so
        gazemouse doesn't need a separate explicit "hold still" step
        before head-tilt scrolling works."""
        if self._baseline is None:
            self.calibrate_baseline(pitch)
            return 0

        deviation = pitch - self._baseline
        if abs(deviation) < self.deadzone:
            return 0
        return round(-deviation * self.scroll_scale)
