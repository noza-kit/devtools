from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest
from PIL import Image

from snapclip.config import Settings
from snapclip.queue import PasteQueue


class FakeScreenCapture:
    """Returns a fixed-color image per call, recording every region
    requested so tests can assert on what was captured."""

    def __init__(self, color=(255, 0, 0), size=(200, 150)):
        self.color = color
        self.size = size
        self.region_calls: list[tuple] = []
        self.fullscreen_calls = 0

    def capture_region(self, rect) -> Image.Image:
        self.region_calls.append(rect)
        w = max(1, rect[2] - rect[0])
        h = max(1, rect[3] - rect[1])
        return Image.new("RGB", (w, h), self.color)

    def capture_fullscreen(self) -> Image.Image:
        self.fullscreen_calls += 1
        return Image.new("RGB", self.size, self.color)


class FakeClipboardBackend:
    """In-memory stand-in for ClipboardBackend, with a manually-driven
    sequence number so tests can simulate "the user copied something
    externally" without touching the real OS clipboard."""

    def __init__(self):
        self._seq = 0
        self._text: Optional[str] = None
        self._image: Optional[Image.Image] = None

    def simulate_external_copy_text(self, text: str) -> None:
        self._seq += 1
        self._text, self._image = text, None

    def simulate_external_copy_image(self, image: Image.Image) -> None:
        self._seq += 1
        self._text, self._image = None, image

    def get_sequence_number(self) -> int:
        return self._seq

    def get_text(self) -> Optional[str]:
        return self._text

    def get_image(self) -> Optional[Image.Image]:
        return self._image

    def set_text(self, text: str) -> None:
        self._seq += 1
        self._text, self._image = text, None

    def set_image(self, image: Image.Image) -> None:
        self._seq += 1
        self._text, self._image = None, image


@pytest.fixture
def fake_capture() -> FakeScreenCapture:
    return FakeScreenCapture()


@pytest.fixture
def fake_clipboard() -> FakeClipboardBackend:
    return FakeClipboardBackend()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(mode="markdown", img_dir=tmp_path / "images")


@pytest.fixture
def queue() -> PasteQueue:
    return PasteQueue()
