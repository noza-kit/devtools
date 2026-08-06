from gazemouse.calibration import calibrate_from_corners
from gazemouse.landmarks import FrameLandmarks, Point
from gazemouse.session import GazeMouseSession, SessionConfig

CORNERS = {
    "top_left": Point(0.3, 0.3),
    "top_right": Point(0.7, 0.3),
    "bottom_left": Point(0.3, 0.7),
    "bottom_right": Point(0.7, 0.7),
}


class FakeMouse:
    def __init__(self):
        self.moves = []
        self.downs = 0
        self.ups = 0
        self.scrolls = []

    def move_to(self, x, y):
        self.moves.append((x, y))

    def mouse_down(self):
        self.downs += 1

    def mouse_up(self):
        self.ups += 1

    def scroll(self, amount):
        self.scrolls.append(amount)


def _session(now_list, screenshot_fn=None, **config_kwargs):
    calibration = calibrate_from_corners(CORNERS, screen_width=1920, screen_height=1080)
    mouse = FakeMouse()
    config = SessionConfig(target_fps=1000, **config_kwargs)  # effectively disable FPS limiting for these tests
    session = GazeMouseSession(mouse, calibration, config=config, screenshot_fn=screenshot_fn, now_fn=lambda: now_list[0])
    return session, mouse


def test_gaze_moves_cursor(face_factory):
    now = [0.0]
    session, mouse = _session(now)
    result = session.process_landmarks(FrameLandmarks(face=face_factory(0.5, 0.5), hand=None))
    assert result["active"] is True
    assert result["moved_to"] == (960, 540)
    assert mouse.moves == [(960, 540)]


def test_no_face_no_hand_frame_is_inactive():
    now = [0.0]
    session, mouse = _session(now)
    result = session.process_landmarks(FrameLandmarks(face=None, hand=None))
    assert result["active"] is False
    assert mouse.moves == []


def test_none_landmarks_is_inactive():
    now = [0.0]
    session, mouse = _session(now)
    result = session.process_landmarks(None)
    assert result["active"] is False


def test_hand_click_press_and_release(face_factory, hand_factory):
    now = [0.0]
    session, mouse = _session(now)
    session.process_landmarks(FrameLandmarks(face=face_factory(), hand=hand_factory(open_hand=True)))
    r_press = session.process_landmarks(FrameLandmarks(face=face_factory(), hand=hand_factory(open_hand=False)))
    assert r_press["click_event"] == "press"
    assert mouse.downs == 1

    r_release = session.process_landmarks(FrameLandmarks(face=face_factory(), hand=hand_factory(open_hand=True)))
    assert r_release["click_event"] == "release"
    assert mouse.ups == 1


def test_drag_holds_mouse_down_while_cursor_moves(face_factory, hand_factory):
    now = [0.0]
    session, mouse = _session(now)
    session.process_landmarks(FrameLandmarks(face=face_factory(0.5, 0.5), hand=hand_factory(open_hand=True)))
    session.process_landmarks(FrameLandmarks(face=face_factory(0.5, 0.5), hand=hand_factory(open_hand=False)))
    assert mouse.downs == 1

    # gaze moves while hand stays closed -- cursor should keep tracking (a drag)
    session.process_landmarks(FrameLandmarks(face=face_factory(0.6, 0.6), hand=hand_factory(open_hand=False)))
    assert mouse.downs == 1  # not re-pressed
    assert mouse.ups == 0  # not released yet
    assert len(mouse.moves) == 3


def test_blink_triggers_screenshot_once(face_factory):
    now = [0.0]
    calls = []
    session, mouse = _session(now, screenshot_fn=lambda: calls.append(1))

    for t in (0.0, 0.5, 1.0, 1.5):
        now[0] = t
        session.process_landmarks(FrameLandmarks(face=face_factory(eyes_open=False)))
    assert calls == []

    now[0] = 2.1
    result = session.process_landmarks(FrameLandmarks(face=face_factory(eyes_open=False)))
    assert result["screenshot"] is True
    assert calls == [1]

    now[0] = 2.5
    result2 = session.process_landmarks(FrameLandmarks(face=face_factory(eyes_open=False)))
    assert result2["screenshot"] is False
    assert calls == [1]  # not re-triggered while still closed


def test_head_tilt_scrolls(face_factory):
    now = [0.0]
    session, mouse = _session(now)
    session.process_landmarks(FrameLandmarks(face=face_factory(pitch=0.30)))  # baseline
    result = session.process_landmarks(FrameLandmarks(face=face_factory(pitch=0.36)))
    assert result["scroll"] != 0
    assert mouse.scrolls == [result["scroll"]]


def test_gaze_and_scroll_are_independent(face_factory):
    """Regression guard for the exact bug the spec calls out: looking
    down to scroll must not also drag the cursor down, since scroll
    uses head pitch (a separate signal) rather than gaze position."""
    now = [0.0]
    session, mouse = _session(now)
    session.process_landmarks(FrameLandmarks(face=face_factory(iris_x=0.5, iris_y=0.5, pitch=0.30)))
    result = session.process_landmarks(FrameLandmarks(face=face_factory(iris_x=0.5, iris_y=0.5, pitch=0.36)))
    assert result["moved_to"] == (960, 540)  # cursor unchanged: gaze (iris) didn't move
    assert result["scroll"] != 0  # but scrolling still happened, from pitch alone


def test_face_lost_mid_session_deactivates(face_factory):
    now = [0.0]
    session, mouse = _session(now)
    session.process_landmarks(FrameLandmarks(face=face_factory(), hand=None))
    result = session.process_landmarks(FrameLandmarks(face=None, hand=None))
    assert result["active"] is False
    assert len(mouse.moves) == 1  # no second move recorded


def test_should_process_frame_rate_limits():
    now = [0.0]
    from gazemouse.calibration import calibrate_from_corners as _cal

    calibration = _cal(CORNERS, 1920, 1080)
    session = GazeMouseSession(FakeMouse(), calibration, config=SessionConfig(target_fps=10.0), now_fn=lambda: now[0])

    assert session.should_process_frame() is True  # first call always processes
    now[0] = 0.05  # 0.05s later, target interval is 0.1s
    assert session.should_process_frame() is False
    now[0] = 0.11
    assert session.should_process_frame() is True
