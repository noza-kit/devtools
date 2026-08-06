from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("airshare.watch")


def find_stale_files(directories: list[Path], expire_days: int, now: Optional[float] = None) -> list[Path]:
    """Files under `directories` (each scanned non-recursively -- these
    are routing destinations, not arbitrary trees) whose last-access
    time is older than `expire_days`. A missing directory is skipped,
    not an error."""
    cutoff = (now if now is not None else time.time()) - expire_days * 86400
    stale = []
    for directory in directories:
        if not directory.exists():
            continue
        for path in directory.iterdir():
            if path.is_file() and path.stat().st_atime < cutoff:
                stale.append(path)
    return stale


def move_to_trash(path: Path) -> None:
    """Moves `path` to the OS recycle bin (per project decision: safer
    default than permanent deletion). Falls back to permanent deletion
    only if send2trash itself isn't installed."""
    try:
        from send2trash import send2trash

        send2trash(str(path))
    except ImportError:
        logger.warning("send2trash not installed; deleting permanently: %s", path)
        path.unlink(missing_ok=True)
