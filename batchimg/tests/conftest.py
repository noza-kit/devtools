from __future__ import annotations

import cv2
import numpy as np
import pytest


@pytest.fixture
def sample_image():
    """A 40x30 BGR image: black background with a white square, so resizing/reading is verifiable."""
    image = np.zeros((30, 40, 3), dtype=np.uint8)
    image[0:15, 0:15] = 255
    return image


def _write_image(path, image=None, size=(40, 30)):
    if image is None:
        w, h = size
        image = np.zeros((h, w, 3), dtype=np.uint8)
        image[0 : h // 2, 0 : w // 2] = 255
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), image)
    return path


def _write_video(path, *, frames=20, size=(64, 48), fps=10.0):
    w, h = size
    path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (w, h))
    for i in range(frames):
        frame = np.full((h, w, 3), i % 255, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    return path


@pytest.fixture
def make_image():
    return _write_image


@pytest.fixture
def make_video():
    return _write_video
