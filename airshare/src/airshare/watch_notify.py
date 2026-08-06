from __future__ import annotations

from pathlib import Path

APP_ID = "AirShare"


def notify_batch(message: str, open_path: Path) -> None:
    """Windows toast notification whose body, when clicked, opens
    `open_path` in Explorer -- `notify` (plyer-based) doesn't expose a
    click callback on every platform it supports, so this uses
    `winotify` directly for this one Windows-specific, click-to-open
    need instead of routing through `notify`. Windows-only, matching
    the rest of this feature's scope."""
    from winotify import Notification

    toast = Notification(app_id=APP_ID, title="ファイルを受信しました", msg=message, launch=str(open_path))
    toast.show()
