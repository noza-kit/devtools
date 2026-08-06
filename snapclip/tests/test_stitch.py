import numpy as np
import pytest
from PIL import Image

from snapclip.stitch import find_vertical_overlap, stitch_vertical


def _synthetic_tall_image(width=300, height=900, seed=1):
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 255, size=(height, width, 3), dtype=np.uint8)
    for y in range(0, height, 30):  # distinctive horizontal bands so it's not pure noise
        arr[y : y + 2, :, :] = [255, 0, 0]
    return Image.fromarray(arr)


def _scroll_frames(master: Image.Image, window_h: int, step: int):
    width, height = master.size
    frames, y = [], 0
    while y + window_h <= height:
        frames.append(master.crop((0, y, width, y + window_h)))
        y += step
    if y < height:
        frames.append(master.crop((0, height - window_h, width, height)))
    return frames


def test_stitch_reconstructs_exact_original():
    master = _synthetic_tall_image()
    frames = _scroll_frames(master, window_h=300, step=220)
    assert len(frames) > 1

    stitched = stitch_vertical(frames)
    assert stitched.size == master.size
    assert np.array_equal(np.array(stitched), np.array(master))


def test_stitch_single_frame_returns_copy():
    master = _synthetic_tall_image(height=300)
    result = stitch_vertical([master])
    assert result.size == master.size
    assert np.array_equal(np.array(result), np.array(master))


def test_stitch_empty_list_raises():
    with pytest.raises(ValueError):
        stitch_vertical([])


def test_stitch_mismatched_widths_raises():
    a = Image.new("RGB", (300, 200))
    b = Image.new("RGB", (250, 200))
    with pytest.raises(ValueError):
        stitch_vertical([a, b])


def test_stitch_handles_small_overlap():
    master = _synthetic_tall_image(height=600)
    frames = _scroll_frames(master, window_h=200, step=190)  # only 10px overlap
    stitched = stitch_vertical(frames)
    assert stitched.height >= master.height - 20  # small overlap should still reconstruct closely


def test_find_vertical_overlap_no_match_returns_zero():
    rng = np.random.default_rng(1)
    frame_a = rng.integers(0, 255, size=(100, 200), dtype=np.uint8)
    frame_b = rng.integers(0, 255, size=(100, 200), dtype=np.uint8)  # unrelated noise
    overlap = find_vertical_overlap(frame_a, frame_b, min_confidence=0.9)
    assert overlap == 0


def test_find_vertical_overlap_mismatched_widths_raises():
    a = np.zeros((100, 200), dtype=np.uint8)
    b = np.zeros((100, 150), dtype=np.uint8)
    with pytest.raises(ValueError):
        find_vertical_overlap(a, b)
