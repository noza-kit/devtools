import numpy as np

from uzbridge.ops import color_range, contour_detect


def test_contour_detect_finds_the_square(sample_image):
    result = contour_detect(sample_image, {}, min_area=50.0)
    assert result["count"] >= 1
    assert any(b["width"] > 0 and b["height"] > 0 for b in result["boxes"])


def test_contour_detect_empty_frame_finds_nothing():
    blank = np.zeros((40, 40, 3), dtype=np.uint8)
    result = contour_detect(blank, {})
    assert result == {"count": 0, "boxes": []}


def test_color_range_finds_matching_blob():
    # Solid yellow-green square, matches the default HSV range.
    frame = np.zeros((40, 40, 3), dtype=np.uint8)
    frame[5:25, 5:25] = (0, 200, 200)  # BGR: yellow-green

    result = color_range(frame, {}, min_area=50.0)
    assert result["found"] is True
    assert 10 < result["cx"] < 20
    assert 10 < result["cy"] < 20


def test_color_range_no_match_reports_not_found(sample_image):
    result = color_range(sample_image, {})
    assert result == {"found": False}
