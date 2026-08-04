import numpy as np
import pytest


@pytest.fixture
def cvprep_home(monkeypatch, tmp_path):
    home = tmp_path / "cvprep_home"
    monkeypatch.setenv("CVPREP_HOME", str(home))
    return home


@pytest.fixture
def sample_image():
    """A 40x40 BGR image: black background with a white 20x20 square in the
    top-left, so ops like edge detection and roi_crop have something to find."""
    image = np.zeros((40, 40, 3), dtype=np.uint8)
    image[0:20, 0:20] = 255
    return image
