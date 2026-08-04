import pytest

from batchimg.resize import InvalidSizeError, compute_target_size, parse_size, resize_image


def test_parse_size_valid():
    assert parse_size("800x600") == (800, 600)
    assert parse_size("800X600") == (800, 600)


@pytest.mark.parametrize("text", ["800", "800x", "x600", "800x600x400", "800xabc", "0x600", "-10x600"])
def test_parse_size_invalid(text):
    with pytest.raises(InvalidSizeError):
        parse_size(text)


def test_compute_target_size_no_keep_aspect_uses_exact_target():
    assert compute_target_size(100, 50, 40, 40, keep_aspect=False) == (40, 40)


def test_compute_target_size_keep_aspect_fits_within_box():
    # 100x50 (2:1) into a 40x40 box -> limited by height ratio -> 40x20? actually width-limited
    assert compute_target_size(100, 50, 40, 40, keep_aspect=True) == (40, 20)


def test_compute_target_size_keep_aspect_portrait():
    # 50x100 (1:2) into a 40x40 box -> height-limited -> 20x40
    assert compute_target_size(50, 100, 40, 40, keep_aspect=True) == (20, 40)


def test_resize_image_produces_expected_shape(sample_image):
    result = resize_image(sample_image, 20, 20, keep_aspect=False)
    assert result.shape[:2] == (20, 20)


def test_resize_image_keep_aspect_shape(sample_image):
    # sample_image is 40x30 (w x h) -> into a 20x20 box, width-limited -> 20x15
    result = resize_image(sample_image, 20, 20, keep_aspect=True)
    assert result.shape[:2] == (15, 20)  # (h, w)
