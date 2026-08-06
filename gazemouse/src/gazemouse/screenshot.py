from __future__ import annotations

import logging
from typing import Callable, Optional

logger = logging.getLogger("gazemouse")


def build_screenshot_fn() -> Optional[Callable[[], None]]:
    """Returns a callable that takes a full-screen stack screenshot via
    snapclip's own capture+queue+markup logic (see
    snapclip.capture.take_stack_screenshot), or None if snapclip isn't
    installed -- gazemouse's 2-second-blink screenshot trigger is then
    simply a no-op rather than a hard dependency/crash. This is the
    "撮影したスクリーンショットは...snapclipのコアロジックや保存先に直接
    連動させる" integration from the spec, done via a direct Python
    import (both tools live in this same repo) rather than shelling
    out to the `snapclip` CLI."""
    try:
        from snapclip.capture import MssScreenCapture, take_stack_screenshot
        from snapclip.config import load_settings
        from snapclip.queue import PasteQueue
    except ImportError:
        logger.warning("snapclip is not installed; blink-triggered screenshots are disabled")
        return None

    capture = MssScreenCapture()
    settings = load_settings()
    queue = PasteQueue()

    def take_screenshot() -> None:
        path = take_stack_screenshot(capture, settings, queue)
        logger.info("blink-triggered screenshot saved: %s", path)

    return take_screenshot
