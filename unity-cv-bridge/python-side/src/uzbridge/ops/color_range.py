from __future__ import annotations

import cv2
import numpy as np

# Default HSV range picks out a yellow-green band; for a different target
# color, register a `functools.partial(color_range, lower=..., upper=...)`
# step instead of editing this default.
DEFAULT_LOWER = (25, 80, 80)
DEFAULT_UPPER = (45, 255, 255)


def color_range(
    frame: np.ndarray,
    context: dict,
    lower: tuple = DEFAULT_LOWER,
    upper: tuple = DEFAULT_UPPER,
    min_area: float = 200.0,
) -> dict:
    """Example pipeline step: report the centroid of the largest blob within
    an HSV color range."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
    else:
        area = 0.0

    if not contours or area < min_area:
        return {"found": False}

    moments = cv2.moments(largest)
    cx = int(moments["m10"] / moments["m00"])
    cy = int(moments["m01"] / moments["m00"])
    return {"found": True, "cx": cx, "cy": cy, "area": area}
