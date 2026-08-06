from __future__ import annotations

from dataclasses import dataclass

from gazemouse.landmarks import Point

CORNER_NAMES = ("top_left", "top_right", "bottom_left", "bottom_right")


class CalibrationError(ValueError):
    pass


@dataclass(frozen=True)
class CalibrationData:
    """The iris-position bounding box observed while looking at each
    screen corner, plus the target screen size. New iris positions are
    linearly mapped (and clamped) from this box onto screen
    coordinates -- a deliberately simple model (not a full projective
    transform) that only needs the 4-corner calibration flow described
    in the spec, at the cost of assuming a roughly rectangular
    (not keystoned) iris-movement range."""

    iris_min_x: float
    iris_max_x: float
    iris_min_y: float
    iris_max_y: float
    screen_width: int
    screen_height: int


def calibrate_from_corners(corner_iris_positions: dict[str, Point], screen_width: int, screen_height: int) -> CalibrationData:
    """`corner_iris_positions` must have all four CORNER_NAMES keys, each
    mapped to the iris Point recorded while the user looked at that
    screen corner."""
    missing = set(CORNER_NAMES) - set(corner_iris_positions)
    if missing:
        raise CalibrationError(f"missing calibration corner(s): {sorted(missing)}")

    xs = [p.x for p in corner_iris_positions.values()]
    ys = [p.y for p in corner_iris_positions.values()]
    data = CalibrationData(
        iris_min_x=min(xs),
        iris_max_x=max(xs),
        iris_min_y=min(ys),
        iris_max_y=max(ys),
        screen_width=screen_width,
        screen_height=screen_height,
    )
    if data.iris_max_x - data.iris_min_x <= 0 or data.iris_max_y - data.iris_min_y <= 0:
        raise CalibrationError("degenerate calibration: no measurable iris movement between corners")
    return data


def map_iris_to_screen(iris: Point, calibration: CalibrationData) -> tuple[float, float]:
    """Linearly maps (and clamps to the screen bounds) an iris position
    into screen pixel coordinates, using the bounding box established
    by calibrate_from_corners()."""
    x_range = calibration.iris_max_x - calibration.iris_min_x
    y_range = calibration.iris_max_y - calibration.iris_min_y

    norm_x = (iris.x - calibration.iris_min_x) / x_range
    norm_y = (iris.y - calibration.iris_min_y) / y_range
    norm_x = min(1.0, max(0.0, norm_x))
    norm_y = min(1.0, max(0.0, norm_y))

    return norm_x * calibration.screen_width, norm_y * calibration.screen_height
