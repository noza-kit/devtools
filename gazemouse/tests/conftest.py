from __future__ import annotations

import pytest

from gazemouse.landmarks import (
    CHIN_INDEX,
    FINGER_PIP_INDICES,
    FINGER_TIP_INDICES,
    FOREHEAD_INDEX,
    LEFT_EYE_EAR_INDICES,
    LEFT_IRIS_CENTER,
    RIGHT_EYE_EAR_INDICES,
    RIGHT_IRIS_CENTER,
    WRIST_INDEX,
    FaceLandmarks,
    HandLandmarks,
    Point,
)


def make_face(iris_x: float = 0.5, iris_y: float = 0.5, eyes_open: bool = True, pitch: float = 0.3) -> FaceLandmarks:
    """A synthetic 478-point face with a controllable iris position,
    eye-openness (drives EAR), and head pitch (chin-to-forehead
    distance). `pitch` is in the same normalized-image-coordinate units
    `estimate_pitch()` returns."""
    points = [Point(0.5, 0.5) for _ in range(478)]
    points[LEFT_IRIS_CENTER] = Point(iris_x, iris_y)
    points[RIGHT_IRIS_CENTER] = Point(iris_x, iris_y)

    vgap = 0.03 if eyes_open else 0.001
    for indices in (LEFT_EYE_EAR_INDICES, RIGHT_EYE_EAR_INDICES):
        # EAR pairs p2<->p6 and p3<->p5 vertically -- each pair needs a
        # shared x-coordinate for the formula to reflect eye-openness.
        outer, up1, up2, inner, low1, low2 = indices
        points[outer] = Point(0.30, 0.40)
        points[inner] = Point(0.40, 0.40)
        points[up1] = Point(0.33, 0.40 - vgap)
        points[up2] = Point(0.37, 0.40 - vgap)
        points[low1] = Point(0.37, 0.40 + vgap)
        points[low2] = Point(0.33, 0.40 + vgap)

    points[FOREHEAD_INDEX] = Point(0.5, 0.2)
    points[CHIN_INDEX] = Point(0.5, 0.2 + pitch)
    return FaceLandmarks(points=points)


def make_hand(open_hand: bool = True) -> HandLandmarks:
    points = [Point(0.5, 0.5) for _ in range(21)]
    points[WRIST_INDEX] = Point(0.5, 0.9)
    for tip_idx, pip_idx in zip(FINGER_TIP_INDICES, FINGER_PIP_INDICES):
        points[pip_idx] = Point(0.5, 0.6)
        points[tip_idx] = Point(0.5, 0.3) if open_hand else Point(0.5, 0.65)
    return HandLandmarks(points=points)


@pytest.fixture
def face_factory():
    return make_face


@pytest.fixture
def hand_factory():
    return make_hand
