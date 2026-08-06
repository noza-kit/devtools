import pytest

from gazemouse.calibration import CalibrationError, calibrate_from_corners, map_iris_to_screen
from gazemouse.landmarks import Point

CORNERS = {
    "top_left": Point(0.3, 0.3),
    "top_right": Point(0.7, 0.3),
    "bottom_left": Point(0.3, 0.7),
    "bottom_right": Point(0.7, 0.7),
}


def test_calibrate_from_corners_computes_bounding_box():
    data = calibrate_from_corners(CORNERS, screen_width=1920, screen_height=1080)
    assert data.iris_min_x == 0.3
    assert data.iris_max_x == 0.7
    assert data.iris_min_y == 0.3
    assert data.iris_max_y == 0.7
    assert data.screen_width == 1920
    assert data.screen_height == 1080


def test_calibrate_missing_corner_raises():
    incomplete = {k: v for k, v in CORNERS.items() if k != "bottom_right"}
    with pytest.raises(CalibrationError):
        calibrate_from_corners(incomplete, 1920, 1080)


def test_calibrate_degenerate_range_raises():
    degenerate = {name: Point(0.5, 0.5) for name in CORNERS}
    with pytest.raises(CalibrationError):
        calibrate_from_corners(degenerate, 1920, 1080)


def test_map_iris_to_screen_center():
    data = calibrate_from_corners(CORNERS, 1920, 1080)
    x, y = map_iris_to_screen(Point(0.5, 0.5), data)
    assert x == pytest.approx(960)
    assert y == pytest.approx(540)


def test_map_iris_to_screen_corner():
    data = calibrate_from_corners(CORNERS, 1920, 1080)
    x, y = map_iris_to_screen(Point(0.3, 0.3), data)
    assert x == pytest.approx(0)
    assert y == pytest.approx(0)

    x, y = map_iris_to_screen(Point(0.7, 0.7), data)
    assert x == pytest.approx(1920)
    assert y == pytest.approx(1080)


def test_map_iris_to_screen_clamps_out_of_range():
    data = calibrate_from_corners(CORNERS, 1920, 1080)
    x, y = map_iris_to_screen(Point(0.0, 0.0), data)  # far outside the calibrated range
    assert x == 0
    assert y == 0

    x, y = map_iris_to_screen(Point(1.0, 1.0), data)
    assert x == 1920
    assert y == 1080
