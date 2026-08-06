from gazemouse.headtilt import HeadTiltScroll, estimate_pitch


def test_estimate_pitch_is_chin_to_forehead_distance(face_factory):
    face = face_factory(pitch=0.3)
    assert estimate_pitch(face) == 0.3


def test_first_call_calibrates_baseline_and_returns_zero():
    scroller = HeadTiltScroll(deadzone=0.01)
    assert scroller.scroll_delta(0.30) == 0


def test_small_deviation_within_deadzone_returns_zero():
    scroller = HeadTiltScroll(deadzone=0.02)
    scroller.scroll_delta(0.30)  # baseline
    assert scroller.scroll_delta(0.31) == 0  # 0.01 deviation < 0.02 deadzone


def test_tilting_down_increases_pitch_and_scrolls_negative():
    scroller = HeadTiltScroll(deadzone=0.01, scroll_scale=100)
    scroller.scroll_delta(0.30)  # baseline
    result = scroller.scroll_delta(0.35)  # tilted down (larger chin-forehead distance)
    assert result < 0


def test_tilting_up_decreases_pitch_and_scrolls_positive():
    scroller = HeadTiltScroll(deadzone=0.01, scroll_scale=100)
    scroller.scroll_delta(0.30)
    result = scroller.scroll_delta(0.25)  # tilted up
    assert result > 0


def test_scroll_scale_affects_magnitude():
    small = HeadTiltScroll(deadzone=0.0, scroll_scale=10)
    large = HeadTiltScroll(deadzone=0.0, scroll_scale=1000)
    small.scroll_delta(0.30)
    large.scroll_delta(0.30)
    assert abs(small.scroll_delta(0.35)) < abs(large.scroll_delta(0.35))


def test_reset_clears_baseline():
    scroller = HeadTiltScroll(deadzone=0.01)
    scroller.scroll_delta(0.30)
    scroller.reset()
    assert scroller.scroll_delta(0.50) == 0  # re-calibrates instead of scrolling
