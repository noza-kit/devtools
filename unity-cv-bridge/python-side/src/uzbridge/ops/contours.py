from __future__ import annotations

import cv2
import numpy as np


def contour_detect(frame: np.ndarray, context: dict, min_area: float = 200.0) -> dict:
    """Example pipeline step: find contours and report their bounding boxes."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        boxes.append({"x": x, "y": y, "width": w, "height": h, "area": area})

    return {"count": len(boxes), "boxes": boxes}
