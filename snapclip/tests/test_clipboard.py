from PIL import Image

from snapclip.clipboard import ClipboardWatcher, Win32ClipboardBackend, deliver_paste_item
from snapclip.queue import PasteQueue, QueueItem


def test_watcher_pushes_external_text_copy(fake_clipboard, queue: PasteQueue):
    watcher = ClipboardWatcher(fake_clipboard, queue)
    pushed = watcher.poll()
    assert pushed is False  # nothing changed yet

    fake_clipboard.simulate_external_copy_text("hello")
    pushed = watcher.poll()
    assert pushed is True
    assert queue.peek_all()[0].content == "hello"


def test_watcher_pushes_external_image_copy(fake_clipboard, queue: PasteQueue):
    watcher = ClipboardWatcher(fake_clipboard, queue)
    img = Image.new("RGB", (10, 10))
    fake_clipboard.simulate_external_copy_image(img)
    assert watcher.poll() is True
    assert queue.peek_all()[0].kind == "image"


def test_watcher_does_not_repush_same_content(fake_clipboard, queue: PasteQueue):
    watcher = ClipboardWatcher(fake_clipboard, queue)
    fake_clipboard.simulate_external_copy_text("hello")
    watcher.poll()
    assert watcher.poll() is False  # sequence number unchanged since last poll
    assert len(queue) == 1


def test_notify_self_set_suppresses_next_poll(fake_clipboard, queue: PasteQueue):
    watcher = ClipboardWatcher(fake_clipboard, queue)
    watcher.notify_self_set()
    fake_clipboard.set_text("delivered by snapclip itself")  # this is what deliver_paste_item does
    assert watcher.poll() is False  # suppressed: this was our own write, not an external copy
    assert len(queue) == 0


def test_deliver_paste_item_writes_clipboard_and_suppresses_watcher(fake_clipboard, queue: PasteQueue):
    watcher = ClipboardWatcher(fake_clipboard, queue)
    calls = []
    deliver_paste_item(QueueItem(kind="text", content="X"), fake_clipboard, watcher, lambda: calls.append("paste"))
    assert fake_clipboard.get_text() == "X"
    assert calls == ["paste"]
    assert watcher.poll() is False  # the write above must not be re-queued


def test_deliver_paste_item_image(fake_clipboard, queue: PasteQueue):
    watcher = ClipboardWatcher(fake_clipboard, queue)
    img = Image.new("RGB", (5, 5))
    deliver_paste_item(QueueItem(kind="image", content=img), fake_clipboard, watcher, lambda: None)
    assert fake_clipboard.get_image() is img


# --- real Windows clipboard integration (this machine's actual OS clipboard) ---
# Confirmed working manually in this environment; these tests do read/write the
# real system clipboard, which is a side effect worth knowing about if run
# alongside something else that's actively using the clipboard.


def test_win32_backend_text_round_trip():
    backend = Win32ClipboardBackend()
    seq_before = backend.get_sequence_number()
    backend.set_text("snapclip real clipboard test")
    assert backend.get_text() == "snapclip real clipboard test"
    assert backend.get_sequence_number() != seq_before


def test_win32_backend_image_round_trip():
    backend = Win32ClipboardBackend()
    backend.set_image(Image.new("RGB", (33, 22), (1, 2, 3)))
    got = backend.get_image()
    assert got is not None
    assert got.size == (33, 22)


def test_win32_backend_sequence_number_changes_on_write():
    backend = Win32ClipboardBackend()
    seq1 = backend.get_sequence_number()
    backend.set_text("first")
    seq2 = backend.get_sequence_number()
    backend.set_text("second")
    seq3 = backend.get_sequence_number()
    assert seq1 != seq2 != seq3
