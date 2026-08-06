from __future__ import annotations

from typing import Callable, Optional, Protocol

from PIL import Image

from snapclip.queue import PasteQueue, QueueItem


class ClipboardBackend(Protocol):
    def get_sequence_number(self) -> int:
        """A number that changes every time the OS clipboard's content
        changes (Windows exposes this natively), used to detect a new
        copy without diffing content on every poll."""
        ...

    def get_text(self) -> Optional[str]: ...
    def get_image(self) -> Optional[Image.Image]: ...
    def set_text(self, text: str) -> None: ...
    def set_image(self, image: Image.Image) -> None: ...


class Win32ClipboardBackend:
    """Real Windows clipboard access via pywin32. All win32 imports are
    lazy so importing this module doesn't require Windows."""

    def get_sequence_number(self) -> int:
        import win32clipboard

        return win32clipboard.GetClipboardSequenceNumber()

    def get_text(self) -> Optional[str]:
        import win32clipboard

        win32clipboard.OpenClipboard()
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            return None
        finally:
            win32clipboard.CloseClipboard()

    def get_image(self) -> Optional[Image.Image]:
        from PIL import ImageGrab

        result = ImageGrab.grabclipboard()
        return result if isinstance(result, Image.Image) else None

    def set_text(self, text: str) -> None:
        import win32clipboard

        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, text)
        finally:
            win32clipboard.CloseClipboard()

    def set_image(self, image: Image.Image) -> None:
        import io

        import win32clipboard

        buf = io.BytesIO()
        image.convert("RGB").save(buf, "BMP")
        dib_bytes = buf.getvalue()[14:]  # strip the 14-byte BMP file header; CF_DIB wants the rest
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, dib_bytes)
        finally:
            win32clipboard.CloseClipboard()


class ClipboardWatcher:
    """Polls a ClipboardBackend's sequence number for changes and pushes
    new copies onto a PasteQueue. `notify_self_set()` must be called
    right after snapclip itself writes to the clipboard (delivering a
    paste-queue item) so that write doesn't get re-queued as if the user
    had copied something new."""

    def __init__(self, backend: ClipboardBackend, queue: PasteQueue):
        self._backend = backend
        self._queue = queue
        self._last_seq = backend.get_sequence_number()
        self._suppress_next = False

    def notify_self_set(self) -> None:
        self._suppress_next = True

    def poll(self) -> bool:
        """Check for a new external clipboard change; push it onto the
        queue if there is one. Returns whether something was pushed."""
        seq = self._backend.get_sequence_number()
        if seq == self._last_seq:
            return False
        self._last_seq = seq

        if self._suppress_next:
            self._suppress_next = False
            return False

        text = self._backend.get_text()
        if text:
            self._queue.push(QueueItem(kind="text", content=text))
            return True

        image = self._backend.get_image()
        if image is not None:
            self._queue.push(QueueItem(kind="image", content=image))
            return True

        return False


def deliver_paste_item(
    item: QueueItem,
    backend: ClipboardBackend,
    watcher: ClipboardWatcher,
    simulate_paste: Callable[[], None],
) -> None:
    """Write `item` to the real OS clipboard and trigger a paste. The
    `watcher.notify_self_set()` call (before `simulate_paste`) is what
    keeps this delivery from being re-queued as a new "external" copy."""
    if item.kind == "text":
        backend.set_text(item.content)
    else:
        backend.set_image(item.content)
    watcher.notify_self_set()
    simulate_paste()
