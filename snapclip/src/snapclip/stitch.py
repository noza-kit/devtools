from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

DEFAULT_STRIP_HEIGHT = 60
DEFAULT_MIN_CONFIDENCE = 0.6


def find_vertical_overlap(
    top_frame: np.ndarray,
    bottom_frame: np.ndarray,
    strip_height: int = DEFAULT_STRIP_HEIGHT,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
) -> int:
    """How many rows at the top of `bottom_frame` duplicate content
    already shown at the bottom of `top_frame`, found by template-
    matching `top_frame`'s bottom strip against all of `bottom_frame`
    (both grayscale 2D arrays of the same width). Returns 0 if no
    confident match is found (frames are treated as non-overlapping --
    a duplicated sliver is a much smaller problem than losing content)."""
    h1, w1 = top_frame.shape
    h2, w2 = bottom_frame.shape
    if w1 != w2:
        raise ValueError("frames must have the same width to stitch")

    strip_height = min(strip_height, h1, h2)
    if strip_height <= 0:
        return 0

    template = top_frame[h1 - strip_height : h1, :]
    result = cv2.matchTemplate(bottom_frame, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    if max_val < min_confidence:
        return 0

    match_y = max_loc[1]  # row in bottom_frame where top_frame's bottom strip was found
    overlap_rows = match_y + strip_height
    return max(0, min(overlap_rows, h2))


def stitch_vertical(
    frames: list[Image.Image],
    strip_height: int = DEFAULT_STRIP_HEIGHT,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
) -> Image.Image:
    """Stitch scroll-captured frames (top-to-bottom, overlapping) into
    one tall image by detecting and dropping each frame's overlap with
    the previous one. All frames must share the same width."""
    if not frames:
        raise ValueError("stitch_vertical requires at least one frame")
    if len(frames) == 1:
        return frames[0].copy()

    width = frames[0].width
    if any(f.width != width for f in frames):
        raise ValueError("all frames must have the same width to stitch")

    pieces = [np.array(frames[0].convert("RGB"))]
    prev_gray = _to_gray(frames[0])

    for frame in frames[1:]:
        cur_gray = _to_gray(frame)
        overlap = find_vertical_overlap(prev_gray, cur_gray, strip_height, min_confidence)
        pieces.append(np.array(frame.convert("RGB"))[overlap:, :, :])
        prev_gray = cur_gray

    non_empty = [p for p in pieces if p.shape[0] > 0]
    combined = np.concatenate(non_empty, axis=0)
    return Image.fromarray(combined)


def _to_gray(image: Image.Image) -> np.ndarray:
    return np.array(image.convert("L"))
