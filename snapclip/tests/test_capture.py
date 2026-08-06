from pathlib import Path

from snapclip.capture import take_stack_screenshot, unique_capture_path
from snapclip.config import Settings
from snapclip.queue import PasteQueue


def test_take_stack_screenshot_saves_file_and_pushes_markup(fake_capture, settings: Settings, queue: PasteQueue):
    path = take_stack_screenshot(fake_capture, settings, queue)
    assert path.exists()
    assert path.parent == settings.img_dir

    items = queue.peek_all()
    assert len(items) == 1
    assert items[0].kind == "text"
    assert str(path).replace("\\", "/") in items[0].content
    assert items[0].content.startswith("![")  # default mode is markdown


def test_take_stack_screenshot_with_region_uses_capture_region(fake_capture, settings: Settings, queue: PasteQueue):
    take_stack_screenshot(fake_capture, settings, queue, region=(10, 20, 110, 170))
    assert fake_capture.region_calls == [(10, 20, 110, 170)]
    assert fake_capture.fullscreen_calls == 0


def test_take_stack_screenshot_without_region_uses_fullscreen(fake_capture, settings: Settings, queue: PasteQueue):
    take_stack_screenshot(fake_capture, settings, queue)
    assert fake_capture.fullscreen_calls == 1


def test_take_stack_screenshot_latex_mode(fake_capture, tmp_path: Path, queue: PasteQueue):
    settings = Settings(mode="latex", img_dir=tmp_path / "figs")
    take_stack_screenshot(fake_capture, settings, queue)
    assert queue.peek_all()[0].content.startswith("\\begin{figure}")


def test_unique_capture_path_avoids_collision(tmp_path: Path):
    from datetime import datetime

    now = datetime(2026, 1, 1, 12, 0, 0)
    first = unique_capture_path(tmp_path, now)
    first.write_bytes(b"x")
    second = unique_capture_path(tmp_path, now)
    assert first != second
    assert second.name == "20260101_120000_1.png"


def test_two_captures_in_same_second_get_distinct_files(fake_capture, settings: Settings, queue: PasteQueue):
    from datetime import datetime

    now = datetime(2026, 1, 1, 12, 0, 0)
    p1 = take_stack_screenshot(fake_capture, settings, queue, now=now)
    p2 = take_stack_screenshot(fake_capture, settings, queue, now=now)
    assert p1 != p2
    assert p1.exists() and p2.exists()
