from gazemouse.handgesture import ClickGestureDetector, is_hand_open


def test_is_hand_open_true_for_open_hand(hand_factory):
    assert is_hand_open(hand_factory(open_hand=True)) is True


def test_is_hand_open_false_for_closed_hand(hand_factory):
    assert is_hand_open(hand_factory(open_hand=False)) is False


def test_no_hand_treated_as_open():
    detector = ClickGestureDetector()
    assert detector.update(None) is None  # starts "open", no hand = no change


def test_open_to_closed_is_press(hand_factory):
    detector = ClickGestureDetector()
    detector.update(hand_factory(open_hand=True))
    assert detector.update(hand_factory(open_hand=False)) == "press"


def test_staying_closed_produces_no_repeated_event(hand_factory):
    detector = ClickGestureDetector()
    detector.update(hand_factory(open_hand=True))
    detector.update(hand_factory(open_hand=False))
    assert detector.update(hand_factory(open_hand=False)) is None
    assert detector.update(hand_factory(open_hand=False)) is None


def test_closed_to_open_is_release(hand_factory):
    detector = ClickGestureDetector()
    detector.update(hand_factory(open_hand=True))
    detector.update(hand_factory(open_hand=False))
    assert detector.update(hand_factory(open_hand=True)) == "release"


def test_full_click_cycle(hand_factory):
    detector = ClickGestureDetector()
    events = [
        detector.update(hand_factory(open_hand=True)),
        detector.update(hand_factory(open_hand=False)),
        detector.update(hand_factory(open_hand=True)),
    ]
    assert events == [None, "press", "release"]


def test_hand_disappearing_mid_press_is_treated_as_release(hand_factory):
    detector = ClickGestureDetector()
    detector.update(hand_factory(open_hand=True))
    detector.update(hand_factory(open_hand=False))
    assert detector.update(None) == "release"  # no hand = "open" = closed->open edge
