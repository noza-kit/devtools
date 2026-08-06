from __future__ import annotations

import time
from typing import Callable, Optional

from snapclip.capture import MssScreenCapture, ScreenCapture, take_stack_screenshot
from snapclip.clipboard import ClipboardBackend, ClipboardWatcher, Win32ClipboardBackend, deliver_paste_item
from snapclip.config import Settings
from snapclip.history import HistoryStore
from snapclip.queue import PasteQueue, QueueItem
from snapclip.scrollcapture import ScrollCaptureSession

DEFAULT_HOTKEYS = {
    "snap": "alt+shift+s",
    "paste": "alt+shift+v",
    "scroll": "alt+shift+c",
}


def _simulate_paste() -> None:
    import keyboard

    keyboard.send("ctrl+v")


class Daemon:
    """Ties the OS-facing pieces (screenshot capture, clipboard,
    scroll-capture state machine, persistent history) together behind
    the three hotkey actions described in the README's "デーモンモード"
    section. `register_hooks()` is the only method that touches real
    global OS hooks (via the `keyboard`/`mouse` packages) — everything
    else here is plain method calls, testable by invoking them
    directly without any OS hook actually firing."""

    def __init__(
        self,
        settings: Settings,
        capture: Optional[ScreenCapture] = None,
        clipboard: Optional[ClipboardBackend] = None,
        history: Optional[HistoryStore] = None,
        hotkeys: Optional[dict] = None,
        paste_mode: str = "one",
        poll_interval: float = 0.2,
        simulate_paste: Callable[[], None] = _simulate_paste,
    ):
        if paste_mode not in ("one", "all"):
            raise ValueError("paste_mode must be 'one' or 'all'")

        self.settings = settings
        self.capture = capture or MssScreenCapture()
        self.clipboard = clipboard or Win32ClipboardBackend()
        self.history = history
        self.hotkeys = {**DEFAULT_HOTKEYS, **(hotkeys or {})}
        self.paste_mode = paste_mode
        self.poll_interval = poll_interval
        self._simulate_paste = simulate_paste

        self.queue = PasteQueue()
        self.watcher = ClipboardWatcher(self.clipboard, self.queue)
        self.scroll_session = ScrollCaptureSession(self.capture, self.settings, self.queue)

    # --- hotkey actions -----------------------------------------------------

    def on_snap(self) -> None:
        path = take_stack_screenshot(self.capture, self.settings, self.queue)
        if self.history:
            self.history.add_text(str(path))

    def on_paste(self) -> None:
        if self.paste_mode == "all":
            items = self.queue.pop_all()
            texts = [str(i.content) for i in items if i.kind == "text"]
            if texts:
                deliver_paste_item(
                    QueueItem(kind="text", content="\n".join(texts)), self.clipboard, self.watcher, self._simulate_paste
                )
            return

        item = self.queue.pop_oldest()
        if item is not None:
            deliver_paste_item(item, self.clipboard, self.watcher, self._simulate_paste)

    def on_scroll_hotkey_down(self) -> None:
        self.scroll_session.start()

    def on_scroll_hotkey_up(self) -> None:
        self.scroll_session.finish()

    def on_mouse_down(self, point) -> None:
        self.scroll_session.on_mouse_down(point)

    def on_mouse_up(self, point) -> None:
        self.scroll_session.on_mouse_up(point)

    def on_wheel(self, *_args) -> None:
        self.scroll_session.on_scroll()

    # --- background clipboard watching --------------------------------------

    def poll_clipboard(self) -> None:
        """Call periodically (see run_forever) to detect external
        clipboard copies and push+record them."""
        if self.watcher.poll() and self.history:
            latest = self.queue.peek_all()
            if latest:
                item = latest[-1]
                if item.kind == "text":
                    self.history.add_text(str(item.content))
                else:
                    self.history.add_image(item.content)

    # --- wiring ---------------------------------------------------------------

    def register_hooks(self, keyboard_module=None, mouse_module=None) -> None:
        """Register the real global hotkey/mouse hooks. Accepts
        `keyboard_module`/`mouse_module` for injection (tests pass a
        fake recorder instead of the real `keyboard`/`mouse` packages,
        which would otherwise install actual OS-level hooks)."""
        if keyboard_module is None:
            import keyboard as keyboard_module
        if mouse_module is None:
            import mouse as mouse_module

        keyboard_module.add_hotkey(self.hotkeys["snap"], self.on_snap)
        keyboard_module.add_hotkey(self.hotkeys["paste"], self.on_paste)

        scroll_key = _primary_key(self.hotkeys["scroll"])
        keyboard_module.on_press_key(scroll_key, lambda _e: self.on_scroll_hotkey_down())
        keyboard_module.on_release_key(scroll_key, lambda _e: self.on_scroll_hotkey_up())

        mouse_module.on_button(
            lambda: self.on_mouse_down(mouse_module.get_position()), buttons=("left",), types=("down",)
        )
        mouse_module.on_button(
            lambda: self.on_mouse_up(mouse_module.get_position()), buttons=("left",), types=("up",)
        )

        # `mouse` has no dedicated on_wheel(); wheel events arrive through
        # its generic hook() alongside move/click events, so we filter for
        # WheelEvent ourselves (falling back to "call on every event" for a
        # test double that doesn't define WheelEvent).
        wheel_event_type = getattr(mouse_module, "WheelEvent", None)

        def _dispatch(event) -> None:
            if wheel_event_type is None or isinstance(event, wheel_event_type):
                self.on_wheel()

        mouse_module.hook(_dispatch)

    def run_forever(self, sleep_fn: Callable[[float], None] = time.sleep) -> None:
        """Blocking loop: registers hooks, then polls the clipboard
        forever (Ctrl+C to stop). The hotkey/mouse callbacks themselves
        run on the `keyboard`/`mouse` packages' own listener threads."""
        self.register_hooks()
        try:
            while True:
                self.poll_clipboard()
                sleep_fn(self.poll_interval)
        except KeyboardInterrupt:
            pass


def _primary_key(combo: str) -> str:
    """"alt+shift+c" -> "c" (the last, non-modifier key — what
    `keyboard.on_press_key`/`on_release_key` key off of; the modifiers
    are expected to already be held per the hold-hotkey UX)."""
    return combo.split("+")[-1].strip()
