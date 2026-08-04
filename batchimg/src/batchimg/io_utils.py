from __future__ import annotations

from pathlib import Path

import cv2


class ImageReadError(Exception):
    pass


def load_image(path: Path):
    image = cv2.imread(str(path))
    if image is None:
        raise ImageReadError(f"Could not read image: {path}")
    return image


def save_image(path: Path, image) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), image):
        raise ImageReadError(f"Could not write image: {path}")
