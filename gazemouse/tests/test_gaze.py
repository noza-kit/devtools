import pytest

from gazemouse.gaze import EmaSmoother


def test_first_sample_returned_unchanged():
    smoother = EmaSmoother(alpha=0.3)
    assert smoother.smooth(10, 20) == (10, 20)


def test_smoothing_moves_toward_new_value_not_all_the_way():
    smoother = EmaSmoother(alpha=0.5)
    smoother.smooth(0, 0)
    x, y = smoother.smooth(10, 10)
    assert 0 < x < 10
    assert x == 5.0  # alpha=0.5 exactly averages


def test_alpha_1_tracks_input_exactly():
    smoother = EmaSmoother(alpha=1.0)
    smoother.smooth(0, 0)
    assert smoother.smooth(100, 200) == (100, 200)


def test_low_alpha_changes_slowly():
    smoother = EmaSmoother(alpha=0.1)
    smoother.smooth(0, 0)
    x, _ = smoother.smooth(100, 100)
    assert x == pytest.approx(10.0)


def test_repeated_smoothing_converges_toward_constant_input():
    smoother = EmaSmoother(alpha=0.3)
    smoother.smooth(0, 0)
    for _ in range(50):
        x, y = smoother.smooth(100, 100)
    assert x == pytest.approx(100, abs=0.01)
    assert y == pytest.approx(100, abs=0.01)


def test_reset_clears_history():
    smoother = EmaSmoother(alpha=0.3)
    smoother.smooth(50, 50)
    smoother.reset()
    assert smoother.smooth(10, 10) == (10, 10)  # first-sample behavior again


def test_invalid_alpha_raises():
    with pytest.raises(ValueError):
        EmaSmoother(alpha=0.0)
    with pytest.raises(ValueError):
        EmaSmoother(alpha=1.5)
