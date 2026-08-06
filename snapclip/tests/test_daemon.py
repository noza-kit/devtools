from pathlib import Path

import pytest

from snapclip.config import Settings
from snapclip.daemon import Daemon
from snapclip.history import HistoryStore
from snapclip.queue import QueueItem


@pytest.fixture
def history_store(tmp_path: Path) -> HistoryStore:
    with HistoryStore(db_path=tmp_path / "h.db", image_dir=tmp_path / "himg") as store:
        yield store


def _daemon(fake_capture, fake_clipboard, settings, history=None, **kwargs) -> Daemon:
    return Daemon(settings, capture=fake_capture, clipboard=fake_clipboard, history=history, **kwargs)


def test_invalid_paste_mode_raises(fake_capture, fake_clipboard, settings):
    with pytest.raises(ValueError):
        _daemon(fake_capture, fake_clipboard, settings, paste_mode="bogus")


def test_on_snap_saves_file_and_records_history(fake_capture, fake_clipboard, settings, history_store):
    d = _daemon(fake_capture, fake_clipboard, settings, history=history_store)
    d.on_snap()
    assert len(d.queue) == 1
    assert len(history_store.all()) == 1


def test_on_paste_one_mode_delivers_oldest_item(fake_capture, fake_clipboard, settings):
    d = _daemon(fake_capture, fake_clipboard, settings, paste_mode="one")
    d.queue.push(QueueItem(kind="text", content="A"))
    d.queue.push(QueueItem(kind="text", content="B"))

    calls = []
    d._simulate_paste = lambda: calls.append("paste")

    d.on_paste()
    assert fake_clipboard.get_text() == "A"
    assert len(d.queue) == 1
    assert calls == ["paste"]

    d.on_paste()
    assert fake_clipboard.get_text() == "B"
    assert len(d.queue) == 0


def test_on_paste_all_mode_joins_and_drains(fake_capture, fake_clipboard, settings):
    d = _daemon(fake_capture, fake_clipboard, settings, paste_mode="all")
    d.queue.push(QueueItem(kind="text", content="A"))
    d.queue.push(QueueItem(kind="text", content="B"))
    d._simulate_paste = lambda: None

    d.on_paste()
    assert fake_clipboard.get_text() == "A\nB"
    assert len(d.queue) == 0


def test_on_paste_empty_queue_is_a_no_op(fake_capture, fake_clipboard, settings):
    d = _daemon(fake_capture, fake_clipboard, settings)
    calls = []
    d._simulate_paste = lambda: calls.append("paste")
    d.on_paste()
    assert calls == []
    assert fake_clipboard.get_text() is None


def test_scroll_hotkey_delegates_to_session(fake_capture, fake_clipboard, settings):
    d = _daemon(fake_capture, fake_clipboard, settings)
    d.on_scroll_hotkey_down()
    assert d.scroll_session.state.value == "selecting_region"
    d.on_mouse_down((0, 0))
    d.on_mouse_up((50, 50))
    assert d.scroll_session.state.value == "capturing"
    d.on_wheel()
    d.on_scroll_hotkey_up()
    assert d.scroll_session.state.value == "idle"


def test_poll_clipboard_records_external_copy_to_history(fake_capture, fake_clipboard, settings, history_store):
    d = _daemon(fake_capture, fake_clipboard, settings, history=history_store)
    fake_clipboard.simulate_external_copy_text("external text")
    d.poll_clipboard()
    assert len(d.queue) == 1
    assert len(history_store.all()) == 1
    assert history_store.all()[0].content == "external text"


def test_poll_clipboard_no_change_records_nothing(fake_capture, fake_clipboard, settings, history_store):
    d = _daemon(fake_capture, fake_clipboard, settings, history=history_store)
    d.poll_clipboard()
    assert len(history_store.all()) == 0


class _FakeHookModule:
    def __init__(self):
        self.hotkeys = {}
        self.press_keys = {}
        self.release_keys = {}
        self.button_hooks = []
        self.hook_calls = []

    def add_hotkey(self, combo, callback):
        self.hotkeys[combo] = callback

    def on_press_key(self, key, callback):
        self.press_keys[key] = callback

    def on_release_key(self, key, callback):
        self.release_keys[key] = callback

    def on_button(self, callback, buttons=(), types=()):
        self.button_hooks.append((callback, buttons, types))

    def hook(self, callback):
        self.hook_calls.append(callback)

    def get_position(self):
        return (0, 0)


def test_register_hooks_wires_expected_hotkeys(fake_capture, fake_clipboard, settings):
    d = _daemon(fake_capture, fake_clipboard, settings)
    fake_keyboard = _FakeHookModule()
    fake_mouse = _FakeHookModule()

    d.register_hooks(keyboard_module=fake_keyboard, mouse_module=fake_mouse)

    assert fake_keyboard.hotkeys["alt+shift+s"] == d.on_snap
    assert fake_keyboard.hotkeys["alt+shift+v"] == d.on_paste
    assert "c" in fake_keyboard.press_keys
    assert "c" in fake_keyboard.release_keys
    assert len(fake_mouse.button_hooks) == 2
    assert len(fake_mouse.hook_calls) == 1


def test_register_hooks_with_real_keyboard_and_mouse_modules_does_not_crash(fake_capture, fake_clipboard, settings):
    """Confirms the real `keyboard`/`mouse` packages accept these
    registrations in this environment (verified manually to work here);
    hooks are torn down immediately after so nothing lingers."""
    import keyboard
    import mouse

    d = _daemon(fake_capture, fake_clipboard, settings, hotkeys={"snap": "ctrl+alt+shift+g", "paste": "ctrl+alt+shift+h", "scroll": "ctrl+alt+shift+j"})
    d.register_hooks()
    keyboard.unhook_all_hotkeys()
    keyboard.unhook_all()
    mouse.unhook_all()
