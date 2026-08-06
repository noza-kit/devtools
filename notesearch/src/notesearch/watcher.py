from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable

logger = logging.getLogger("notesearch")


def run_daemon(target_dirs: list[Path], on_change: Callable[[], None], poll_interval: float = 5.0) -> None:
    """Background auto-sync mode (opt-in alternative to the default
    JIT-sync-on-search): watches `target_dirs` for filesystem changes
    via `watchdog` and calls `on_change()` (expected to be a thin
    wrapper around sync.sync_index()) whenever something changes,
    coalesced to at most once per `poll_interval` seconds rather than
    once per individual file event (a save-triggered multi-file editor
    write, or a git checkout touching many files, would otherwise
    trigger a re-sync per file). Blocks until Ctrl+C."""
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    dirty = {"changed": False}

    class _Handler(FileSystemEventHandler):
        def on_any_event(self, event):
            if not event.is_directory:
                dirty["changed"] = True

    observer = Observer()
    handler = _Handler()
    watched_any = False
    for target_dir in target_dirs:
        if target_dir.exists():
            observer.schedule(handler, str(target_dir), recursive=True)
            watched_any = True
        else:
            logger.warning("target_dirs entry does not exist, not watching: %s", target_dir)

    if not watched_any:
        raise ValueError("no existing target_dirs to watch")

    observer.start()
    try:
        while True:
            time.sleep(poll_interval)
            if dirty["changed"]:
                dirty["changed"] = False
                on_change()
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()
