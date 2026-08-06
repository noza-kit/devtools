from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional, Protocol, Tuple

from PIL import Image

from snapclip.config import Settings
from snapclip.markup import generate_filename, render_markup
from snapclip.queue import PasteQueue, QueueItem

Rect = Tuple[int, int, int, int]  # (left, top, right, bottom), screen pixels


class ScreenCapture(Protocol):
    def capture_region(self, rect: Rect) -> Image.Image: ...
    def capture_fullscreen(self) -> Image.Image: ...


class MssScreenCapture:
    """Real screen capture via mss. Imports mss lazily so importing this
    module doesn't require a display/mss to be available (e.g. in CI)."""

    def capture_region(self, rect: Rect) -> Image.Image:
        import mss

        left, top, right, bottom = rect
        monitor = {"left": left, "top": top, "width": right - left, "height": bottom - top}
        with mss.mss() as sct:
            shot = sct.grab(monitor)
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    def capture_fullscreen(self) -> Image.Image:
        import mss

        with mss.mss() as sct:
            shot = sct.grab(sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0])
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


def take_stack_screenshot(
    capture: ScreenCapture,
    settings: Settings,
    queue: PasteQueue,
    region: Optional[Rect] = None,
    now: Optional[datetime] = None,
) -> Path:
    """Capture (region if given, else the full screen), save it under
    `settings.img_dir`, and push its rendered Markdown/LaTeX markup onto
    `queue` (not the raw image — see PasteQueue's docstring). Returns
    the saved file's path."""
    image = capture.capture_region(region) if region else capture.capture_fullscreen()

    settings.img_dir.mkdir(parents=True, exist_ok=True)
    path = unique_capture_path(settings.img_dir, now)
    image.save(path)

    queue.push(QueueItem(kind="text", content=render_markup(settings.mode, path)))
    return path


def unique_capture_path(img_dir: Path, now: Optional[datetime]) -> Path:
    now = now or datetime.now()
    path = img_dir / generate_filename(now)
    suffix = 1
    while path.exists():
        path = img_dir / generate_filename(now, suffix=str(suffix))
        suffix += 1
    return path
