from __future__ import annotations

import logging
import time
from collections import Counter
from pathlib import Path
from typing import Callable, Optional

from airshare.watch_config import WatchSettings
from airshare.watch_cleanup import find_stale_files, move_to_trash
from airshare.watch_events import DebounceTracker
from airshare.watch_hooks import run_hooks_for_file
from airshare.watch_routing import route_file

logger = logging.getLogger("airshare.watch")

CLEANUP_INTERVAL_SECONDS = 86400  # once a day


def format_batch_message(moved: list[Path], compressed_count: int = 0) -> str:
    counts = Counter(p.parent.name for p in moved)
    breakdown = ", ".join(f"{name} {n}件" for name, n in counts.items())
    message = f"{len(moved)}件のファイルを受信しました: {breakdown}"
    if compressed_count:
        message += f"(うち{compressed_count}件は処理済み)"
    return message


class WatchDaemon:
    """The OS-independent core of `airshare watch start`: an event
    (from a real watchdog hook, or a test calling on_fs_event directly)
    feeds the debounce tracker; process_ready_batch(), called
    periodically, routes+hooks whatever's settled and fires one
    notification for the batch. No OS dependency of its own -- see
    run_watch_daemon() for the real watchdog/winotify wiring."""

    def __init__(
        self,
        settings: WatchSettings,
        notify_fn: Callable[[str, Path, int], None],
        now_fn: Callable[[], float] = time.monotonic,
    ):
        self.settings = settings
        self._tracker = DebounceTracker(settings.debounce_seconds, now_fn=now_fn)
        self._notify_fn = notify_fn

    def on_fs_event(self, path: Path) -> None:
        self._tracker.notify_event(path)

    def process_ready_batch(self) -> list[Path]:
        ready = [p for p in self._tracker.ready_batch() if p.exists()]
        if not ready:
            return []

        moved: list[Path] = []
        hook_successes = 0
        for path in ready:
            new_path = route_file(path, self.settings.routing, fallback=self.settings.inbox_dir)
            hook_result = run_hooks_for_file(self.settings.hooks, new_path)
            if hook_result:
                hook_successes += 1
            moved.append(new_path)

        message = format_batch_message(moved, compressed_count=hook_successes)
        open_path = moved[0].parent if len({p.parent for p in moved}) == 1 else self.settings.inbox_dir
        self._notify_fn(message, open_path, len(moved))

        return moved

    def run_cleanup(self) -> list[Path]:
        if not self.settings.cleanup.enabled:
            return []
        directories = [rule.destination for rule in self.settings.routing] + [self.settings.inbox_dir]
        stale = find_stale_files(directories, self.settings.cleanup.expire_days)
        for path in stale:
            move_to_trash(path)
        return stale


def _default_notify_and_log(message: str, open_path: Path, file_count: int) -> None:
    from airshare.watch_notify import notify_batch
    from airshare.watch_state import append_log_entry

    notify_batch(message, open_path)
    append_log_entry(message, file_count)


def run_watch_daemon(
    settings: WatchSettings,
    notify_fn: Optional[Callable[[str, Path, int], None]] = None,
    poll_interval: float = 1.0,
) -> None:
    """Registers a real watchdog observer on `settings.inbox_dir` and
    drives WatchDaemon's periodic methods forever (Ctrl+C to stop)."""
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    daemon = WatchDaemon(settings, notify_fn or _default_notify_and_log)

    class _Handler(FileSystemEventHandler):
        def on_created(self, event) -> None:
            if not event.is_directory:
                daemon.on_fs_event(Path(event.src_path))

        def on_modified(self, event) -> None:
            if not event.is_directory:
                daemon.on_fs_event(Path(event.src_path))

        def on_moved(self, event) -> None:
            if not event.is_directory:
                daemon.on_fs_event(Path(event.dest_path))

    from airshare.watch_state import clear_watch_runtime_info, write_watch_runtime_info

    settings.inbox_dir.mkdir(parents=True, exist_ok=True)
    observer = Observer()
    observer.schedule(_Handler(), str(settings.inbox_dir), recursive=False)
    observer.start()
    write_watch_runtime_info()

    last_cleanup = time.time()
    try:
        while True:
            time.sleep(poll_interval)
            daemon.process_ready_batch()
            if time.time() - last_cleanup >= CLEANUP_INTERVAL_SECONDS:
                removed = daemon.run_cleanup()
                if removed:
                    logger.info("cleanup: moved %d stale file(s) to the recycle bin", len(removed))
                last_cleanup = time.time()
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()
        clear_watch_runtime_info()
