from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


class ImageReadError(Exception):
    pass


def load_image(path):
    path = Path(path)
    image = cv2.imread(str(path))
    if image is None:
        raise ImageReadError(f"Could not read image: {path}")
    return image


def save_image(path, image) -> None:
    """Write an image (or array produced by a pipeline) to disk.

    ``.npy`` paths save the raw array as-is (use this to keep float output
    from e.g. `normalize` exact). Any other extension goes through
    `cv2.imwrite`; floating-point arrays are min-max rescaled to uint8 first
    since image codecs can't represent arbitrary float ranges.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.suffix == ".npy":
        np.save(path, image)
        return

    if np.issubdtype(image.dtype, np.floating):
        image = _float_to_uint8(image)

    if not cv2.imwrite(str(path), image):
        raise ImageReadError(f"Could not write image: {path}")


def _float_to_uint8(image):
    lo, hi = float(image.min()), float(image.max())
    if hi > lo:
        image = (image - lo) / (hi - lo)
    else:
        image = np.zeros_like(image)
    return (image * 255).astype("uint8")
