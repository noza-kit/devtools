import numpy as np
import pytest

from cvprep.io import ImageReadError, load_image, save_image


def test_save_and_load_roundtrip(tmp_path, sample_image):
    path = tmp_path / "out.png"
    save_image(path, sample_image)
    loaded = load_image(path)
    assert loaded.shape == sample_image.shape


def test_save_float_array_rescales_to_uint8(tmp_path, sample_image):
    normalized = sample_image.astype("float32") / 255.0
    path = tmp_path / "out.png"
    save_image(path, normalized)
    loaded = load_image(path)
    assert loaded.dtype == np.uint8
    assert loaded.max() > 0


def test_save_npy_preserves_float_values(tmp_path, sample_image):
    normalized = sample_image.astype("float32") / 255.0
    path = tmp_path / "out.npy"
    save_image(path, normalized)
    loaded = np.load(path)
    np.testing.assert_array_equal(loaded, normalized)


def test_save_creates_parent_directories(tmp_path, sample_image):
    path = tmp_path / "nested" / "dir" / "out.png"
    save_image(path, sample_image)
    assert path.exists()


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(ImageReadError):
        load_image(tmp_path / "missing.png")
