import cv2
import numpy as np
import pytest


@pytest.fixture
def sample_image():
    """A 40x40 BGR image: black background with a white 20x20 square, inset
    from the edges so Canny/contour detection sees a fully closed boundary
    (a square flush against the frame border won't form a closed contour)."""
    image = np.zeros((40, 40, 3), dtype=np.uint8)
    image[5:25, 5:25] = 255
    return image


@pytest.fixture
def sample_jpeg(sample_image):
    ok, jpeg = cv2.imencode(".jpg", sample_image)
    assert ok
    return jpeg.tobytes()
