import numpy as np
import pytest

from cvprep import ops


def test_resize_explicit_size(sample_image):
    out = ops.resize(sample_image, width=20, height=10)
    assert out.shape[:2] == (10, 20)


def test_resize_preserves_aspect_ratio_with_one_dimension(sample_image):
    out = ops.resize(sample_image, width=20)
    assert out.shape[:2] == (20, 20)


def test_resize_by_scale(sample_image):
    out = ops.resize(sample_image, scale=0.5)
    assert out.shape[:2] == (20, 20)


def test_resize_requires_a_dimension(sample_image):
    with pytest.raises(ValueError):
        ops.resize(sample_image)


def test_normalize_default_scales_to_unit_range(sample_image):
    out = ops.normalize(sample_image)
    assert out.dtype == np.float32
    assert out.max() <= 1.0
    assert out.min() >= 0.0


def test_normalize_applies_mean_and_std(sample_image):
    out = ops.normalize(sample_image, mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
    white_pixel = out[0, 0]
    np.testing.assert_allclose(white_pixel, [1.0, 1.0, 1.0], atol=1e-5)


def test_roi_crop(sample_image):
    out = ops.roi_crop(sample_image, x=0, y=0, width=20, height=20)
    assert out.shape == (20, 20, 3)
    assert (out == 255).all()


def test_grayscale_reduces_channels(sample_image):
    out = ops.grayscale(sample_image)
    assert out.ndim == 2
    assert out.shape == (40, 40)


def test_grayscale_is_noop_on_grayscale_input(sample_image):
    gray = ops.grayscale(sample_image)
    assert ops.grayscale(gray) is gray


def test_blur_preserves_shape(sample_image):
    out = ops.blur(sample_image, ksize=5)
    assert out.shape == sample_image.shape


def test_blur_rounds_even_ksize_up(sample_image):
    even = ops.blur(sample_image, ksize=4)
    odd = ops.blur(sample_image, ksize=5)
    np.testing.assert_array_equal(even, odd)


def test_canny_edge_detects_the_square_border(sample_image):
    out = ops.canny_edge(sample_image, threshold1=50, threshold2=150)
    assert out.ndim == 2
    assert out.dtype == np.uint8
    assert out.max() == 255  # some edge pixels found


def test_threshold_binary_produces_two_values(sample_image):
    out = ops.threshold(sample_image, thresh=127, method="binary")
    assert set(np.unique(out).tolist()) <= {0, 255}


def test_threshold_unknown_method_raises(sample_image):
    with pytest.raises(ValueError):
        ops.threshold(sample_image, method="nope")


def test_rotate_preserves_shape(sample_image):
    out = ops.rotate(sample_image, angle=45)
    assert out.shape == sample_image.shape


def test_flip_horizontal_mirrors_columns(sample_image):
    out = ops.flip(sample_image, mode="horizontal")
    np.testing.assert_array_equal(out, sample_image[:, ::-1])


def test_flip_unknown_mode_raises(sample_image):
    with pytest.raises(ValueError):
        ops.flip(sample_image, mode="sideways")


def test_equalize_hist_preserves_shape(sample_image):
    out = ops.equalize_hist(sample_image)
    assert out.shape == (40, 40)


def test_denoise_preserves_shape(sample_image):
    out = ops.denoise(sample_image)
    assert out.shape == sample_image.shape
