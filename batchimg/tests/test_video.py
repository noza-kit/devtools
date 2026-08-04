import cv2
import pytest

from batchimg.video import VideoReadError, process_video


def _frame_count(path):
    cap = cv2.VideoCapture(str(path))
    count = 0
    while True:
        ok, _ = cap.read()
        if not ok:
            break
        count += 1
    cap.release()
    return count


def test_process_video_copies_frame_count_when_no_options(tmp_path, make_video):
    src = make_video(tmp_path / "in.mp4", frames=20, size=(64, 48), fps=10.0)
    dst = tmp_path / "out.mp4"

    written = process_video(src, dst)

    assert written == 20
    assert dst.exists()
    assert _frame_count(dst) == 20


def test_process_video_resizes_frames(tmp_path, make_video):
    src = make_video(tmp_path / "in.mp4", frames=10, size=(64, 48), fps=10.0)
    dst = tmp_path / "out.mp4"

    process_video(src, dst, target_size=(32, 32), keep_aspect=False)

    cap = cv2.VideoCapture(str(dst))
    ok, frame = cap.read()
    cap.release()
    assert ok
    assert frame.shape[:2] == (32, 32)


def test_process_video_trims_frame_range(tmp_path, make_video):
    src = make_video(tmp_path / "in.mp4", frames=20, size=(64, 48), fps=10.0)
    dst = tmp_path / "out.mp4"

    written = process_video(src, dst, trim_start=0.5, trim_end=1.0)

    # 0.5s..1.0s @ 10fps -> frames [5, 10) -> 5 frames
    assert written == 5
    assert _frame_count(dst) == 5


def test_process_video_missing_source_raises(tmp_path):
    with pytest.raises(VideoReadError):
        process_video(tmp_path / "missing.mp4", tmp_path / "out.mp4")


def test_process_video_trim_beyond_video_raises_and_cleans_up(tmp_path, make_video):
    src = make_video(tmp_path / "in.mp4", frames=10, size=(64, 48), fps=10.0)
    dst = tmp_path / "out.mp4"

    with pytest.raises(VideoReadError):
        process_video(src, dst, trim_start=5.0, trim_end=None)

    assert not dst.exists()
