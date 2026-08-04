from __future__ import annotations

import cv2


class InvalidSizeError(Exception):
    pass


def parse_size(text: str) -> tuple[int, int]:
    """Parse a "WIDTHxHEIGHT" string, e.g. "800x600"."""
    parts = text.lower().split("x")
    if len(parts) != 2:
        raise InvalidSizeError(f"Invalid size '{text}', expected WIDTHxHEIGHT e.g. 800x600")
    try:
        width, height = int(parts[0]), int(parts[1])
    except ValueError as exc:
        raise InvalidSizeError(f"Invalid size '{text}', expected WIDTHxHEIGHT e.g. 800x600") from exc
    if width <= 0 or height <= 0:
        raise InvalidSizeError(f"Size must be positive: '{text}'")
    return width, height


def compute_target_size(orig_w: int, orig_h: int, target_w: int, target_h: int, keep_aspect: bool) -> tuple[int, int]:
    """Compute the actual output size for an `orig_w`x`orig_h` image."""
    if not keep_aspect:
        return target_w, target_h
    scale = min(target_w / orig_w, target_h / orig_h)
    new_w = max(1, round(orig_w * scale))
    new_h = max(1, round(orig_h * scale))
    return new_w, new_h


def resize_image(image, target_w: int, target_h: int, keep_aspect: bool):
    orig_h, orig_w = image.shape[:2]
    new_w, new_h = compute_target_size(orig_w, orig_h, target_w, target_h, keep_aspect)
    interpolation = cv2.INTER_AREA if (new_w * new_h) <= (orig_w * orig_h) else cv2.INTER_LINEAR
    return cv2.resize(image, (new_w, new_h), interpolation=interpolation)
