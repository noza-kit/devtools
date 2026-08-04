import pytest

from batchimg.io_utils import ImageReadError, load_image, save_image


def test_load_image_roundtrip(tmp_path, sample_image):
    path = tmp_path / "in.png"
    save_image(path, sample_image)

    loaded = load_image(path)

    assert loaded.shape == sample_image.shape


def test_load_image_missing_file_raises(tmp_path):
    with pytest.raises(ImageReadError):
        load_image(tmp_path / "missing.png")


def test_load_image_corrupt_file_raises(tmp_path):
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"not an image")

    with pytest.raises(ImageReadError):
        load_image(bad)


def test_save_image_creates_parent_directories(tmp_path, sample_image):
    path = tmp_path / "nested" / "dir" / "out.png"

    save_image(path, sample_image)

    assert path.exists()
