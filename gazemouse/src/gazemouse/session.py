from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional

from gazemouse.blink import DEFAULT_EAR_THRESHOLD, DEFAULT_HOLD_SECONDS, BlinkDetector, face_ear
from gazemouse.calibration import CalibrationData, map_iris_to_screen
from gazemouse.gaze import EmaSmoother
from gazemouse.handgesture import ClickGestureDetector
from gazemouse.headtilt import DEFAULT_DEADZONE, DEFAULT_SCROLL_SCALE, HeadTiltScroll, estimate_pitch
from gazemouse.landmarks import LEFT_IRIS_CENTER, RIGHT_IRIS_CENTER, FrameLandmarks, Point
from gazemouse.mouse_control import MouseController
from gazemouse.safety import SafetyMonitor

DEFAULT_TARGET_FPS = 17.0  # within the spec's 15-20fps power/perf budget


@dataclass(frozen=True)
class SessionConfig:
    ema_alpha: float = 0.3
    ear_threshold: float = DEFAULT_EAR_THRESHOLD
    blink_hold_seconds: float = DEFAULT_HOLD_SECONDS
    target_fps: float = DEFAULT_TARGET_FPS
    scroll_deadzone: float = DEFAULT_DEADZONE
    scroll_scale: float = DEFAULT_SCROLL_SCALE


class GazeMouseSession:
    """The per-frame pipeline: gaze->cursor (EMA-smoothed), hand
    open/close->mouse press/release, sustained-eye-closure->screenshot,
    head-tilt->scroll, gated by SafetyMonitor. No OS/camera dependency
    of its own -- `process_landmarks()` takes plain FrameLandmarks (from
    a real MediaPipeLandmarkSource in production, or a fake one in
    tests) and drives a `MouseController` (real or fake) accordingly,
    so the entire decision logic here is fully unit-testable."""

    def __init__(
        self,
        mouse: MouseController,
        calibration: CalibrationData,
        config: Optional[SessionConfig] = None,
        screenshot_fn: Optional[Callable[[], None]] = None,
        now_fn: Callable[[], float] = time.monotonic,
    ):
        self.mouse = mouse
        self.calibration = calibration
        self.config = config or SessionConfig()
        self.screenshot_fn = screenshot_fn
        self._now = now_fn

        self.smoother = EmaSmoother(self.config.ema_alpha)
        self.blink_detector = BlinkDetector(self.config.ear_threshold, self.config.blink_hold_seconds, now_fn=now_fn)
        self.click_detector = ClickGestureDetector()
        self.head_tilt = HeadTiltScroll(self.config.scroll_deadzone, self.config.scroll_scale)
        self.safety = SafetyMonitor()

        # -inf (not 0.0) so the very first should_process_frame() call always
        # passes, regardless of what now_fn() happens to return initially --
        # a real time.monotonic() is usually already far from 0 in practice,
        # but a fake now_fn in tests (or a clock that starts at/near 0) would
        # otherwise make the first real frame spuriously get dropped.
        self._last_frame_time = float("-inf")

    def should_process_frame(self) -> bool:
        """FPS limiting: call once per captured camera frame; returns
        whether enough time has passed since the last *processed*
        frame to process this one too, per `config.target_fps`. A
        camera producing frames faster than that (most webcams
        default to 30/60fps) has the excess silently dropped rather
        than processed, capping CPU/GPU load."""
        now = self._now()
        if now - self._last_frame_time >= 1.0 / self.config.target_fps:
            self._last_frame_time = now
            return True
        return False

    def process_landmarks(self, landmarks: Optional[FrameLandmarks]) -> dict:
        """Runs one frame's worth of decisions. Returns a small summary
        dict (mainly for tests/logging) of what happened: {"active":
        bool, "moved_to": (x,y)|None, "click_event": str|None,
        "screenshot": bool, "scroll": int}."""
        face = landmarks.face if landmarks else None
        hand = landmarks.hand if landmarks else None

        self.safety.update_face_visibility(face is not None)
        if not self.safety.is_active:
            return {"active": False, "moved_to": None, "click_event": None, "screenshot": False, "scroll": 0}

        result = {"active": True, "moved_to": None, "click_event": None, "screenshot": False, "scroll": 0}

        if face is not None:
            iris = _average_point(face.points[LEFT_IRIS_CENTER], face.points[RIGHT_IRIS_CENTER])
            screen_x, screen_y = map_iris_to_screen(iris, self.calibration)
            smooth_x, smooth_y = self.smoother.smooth(screen_x, screen_y)
            self.mouse.move_to(round(smooth_x), round(smooth_y))
            result["moved_to"] = (round(smooth_x), round(smooth_y))

            if self.blink_detector.update(face_ear(face)):
                result["screenshot"] = True
                if self.screenshot_fn:
                    self.screenshot_fn()

            scroll = self.head_tilt.scroll_delta(estimate_pitch(face))
            if scroll:
                self.mouse.scroll(scroll)
                result["scroll"] = scroll

        click_event = self.click_detector.update(hand)
        if click_event == "press":
            self.mouse.mouse_down()
            result["click_event"] = "press"
        elif click_event == "release":
            self.mouse.mouse_up()
            result["click_event"] = "release"

        return result


def _average_point(a: Point, b: Point) -> Point:
    return Point((a.x + b.x) / 2, (a.y + b.y) / 2, (a.z + b.z) / 2)
