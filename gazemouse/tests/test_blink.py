from gazemouse.blink import BlinkDetector, eye_aspect_ratio, face_ear
from gazemouse.landmarks import LEFT_EYE_EAR_INDICES


def test_eye_aspect_ratio_open_is_larger_than_closed(face_factory):
    open_face = face_factory(eyes_open=True)
    closed_face = face_factory(eyes_open=False)
    open_ear = eye_aspect_ratio([open_face.points[i] for i in LEFT_EYE_EAR_INDICES])
    closed_ear = eye_aspect_ratio([closed_face.points[i] for i in LEFT_EYE_EAR_INDICES])
    assert open_ear > closed_ear


def test_face_ear_is_minimum_of_both_eyes(face_factory):
    face = face_factory(eyes_open=True)
    ear = face_ear(face)
    assert ear > 0


def test_ordinary_blink_does_not_trigger(face_factory):
    now = [0.0]
    detector = BlinkDetector(hold_seconds=2.0, now_fn=lambda: now[0])
    closed_ear = face_ear(face_factory(eyes_open=False))

    now[0] = 0.0
    assert detector.update(closed_ear) is False
    now[0] = 0.2  # a normal 0.2s blink
    assert detector.update(closed_ear) is False
    now[0] = 0.25
    open_ear = face_ear(face_factory(eyes_open=True))
    assert detector.update(open_ear) is False  # eyes reopened before the hold threshold


def test_sustained_closure_triggers_once(face_factory):
    now = [0.0]
    detector = BlinkDetector(hold_seconds=2.0, now_fn=lambda: now[0])
    closed_ear = face_ear(face_factory(eyes_open=False))

    now[0] = 0.0
    assert detector.update(closed_ear) is False
    now[0] = 1.0
    assert detector.update(closed_ear) is False
    now[0] = 2.1
    assert detector.update(closed_ear) is True  # fires exactly here
    now[0] = 2.5
    assert detector.update(closed_ear) is False  # not re-fired while still closed


def test_reopening_and_reclosing_resets_the_timer(face_factory):
    now = [0.0]
    detector = BlinkDetector(hold_seconds=2.0, now_fn=lambda: now[0])
    closed_ear = face_ear(face_factory(eyes_open=False))
    open_ear = face_ear(face_factory(eyes_open=True))

    now[0] = 0.0
    detector.update(closed_ear)
    now[0] = 1.9
    assert detector.update(closed_ear) is False
    now[0] = 1.95
    detector.update(open_ear)  # reopen just before the threshold
    now[0] = 3.0  # re-closes here -- the hold timer restarts from this point, not from t=0
    detector.update(closed_ear)
    now[0] = 4.9  # 1.9s since re-closing at t=3.0: not yet 2.0s
    assert detector.update(closed_ear) is False
    now[0] = 5.1  # 2.1s since re-closing at t=3.0: threshold crossed
    assert detector.update(closed_ear) is True


def test_can_trigger_again_after_reopening(face_factory):
    now = [0.0]
    detector = BlinkDetector(hold_seconds=2.0, now_fn=lambda: now[0])
    closed_ear = face_ear(face_factory(eyes_open=False))
    open_ear = face_ear(face_factory(eyes_open=True))

    now[0] = 0.0
    detector.update(closed_ear)
    now[0] = 2.1
    assert detector.update(closed_ear) is True

    now[0] = 2.2
    detector.update(open_ear)
    now[0] = 2.3
    detector.update(closed_ear)
    now[0] = 4.4
    assert detector.update(closed_ear) is True
