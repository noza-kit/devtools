from pathlib import Path

from airshare.watch_notify import notify_batch


def test_notify_batch_does_not_raise():
    """Confirmed manually to actually pop a Windows toast in this
    environment; here we just confirm the call succeeds without
    raising (there's no automated way to assert a toast was visually
    shown -- see snapclip's real-clipboard tests for the same kind of
    "call the real OS API, assert no exception" pattern used
    elsewhere in this repo)."""
    notify_batch("2件のファイルを受信しました: Pictures 1件, Documents 1件", Path.home())
