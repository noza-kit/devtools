import time
from pathlib import Path

from airshare.watch_config import CleanupSettings, RoutingRule, WatchSettings
from airshare.watch_daemon import WatchDaemon, format_batch_message


def test_format_batch_message_groups_by_destination():
    moved = [Path("/Pictures/a.jpg"), Path("/Pictures/b.jpg"), Path("/Documents/c.pdf")]
    message = format_batch_message(moved)
    assert "3件のファイルを受信しました" in message
    assert "Pictures 2件" in message
    assert "Documents 1件" in message


def test_format_batch_message_with_compressed_count():
    moved = [Path("/Documents/a.pdf")]
    message = format_batch_message(moved, compressed_count=1)
    assert "うち1件は処理済み" in message


def test_format_batch_message_no_hooks_omits_processed_note():
    moved = [Path("/Documents/a.pdf")]
    message = format_batch_message(moved, compressed_count=0)
    assert "処理済み" not in message


def _settings(tmp_path: Path, debounce=1.0) -> WatchSettings:
    return WatchSettings(
        inbox_dir=tmp_path / "inbox",
        debounce_seconds=debounce,
        routing=(RoutingRule(name="pics", extensions=(".jpg",), destination=tmp_path / "Pictures"),),
        cleanup=CleanupSettings(enabled=True, expire_days=7),
    )


def test_process_ready_batch_routes_and_notifies(tmp_path: Path):
    settings = _settings(tmp_path)
    settings.inbox_dir.mkdir(parents=True)
    (settings.inbox_dir / "photo.jpg").write_bytes(b"x")

    notified = []
    now = [0.0]
    daemon = WatchDaemon(settings, lambda msg, path, count: notified.append((msg, path, count)), now_fn=lambda: now[0])

    daemon.on_fs_event(settings.inbox_dir / "photo.jpg")
    assert daemon.process_ready_batch() == []  # debounce hasn't elapsed

    now[0] = 2.0
    moved = daemon.process_ready_batch()

    assert moved == [tmp_path / "Pictures" / "photo.jpg"]
    assert moved[0].exists()
    assert len(notified) == 1
    assert notified[0][2] == 1


def test_process_ready_batch_empty_when_nothing_pending(tmp_path: Path):
    settings = _settings(tmp_path)
    daemon = WatchDaemon(settings, lambda *a: None)
    assert daemon.process_ready_batch() == []


def test_process_ready_batch_skips_files_that_vanished(tmp_path: Path):
    settings = _settings(tmp_path)
    settings.inbox_dir.mkdir(parents=True)
    now = [0.0]
    daemon = WatchDaemon(settings, lambda *a: None, now_fn=lambda: now[0])

    ghost_path = settings.inbox_dir / "ghost.jpg"  # never actually created on disk
    daemon.on_fs_event(ghost_path)
    now[0] = 2.0
    assert daemon.process_ready_batch() == []


def test_run_cleanup_disabled_returns_empty(tmp_path: Path):
    settings = WatchSettings(inbox_dir=tmp_path, cleanup=CleanupSettings(enabled=False))
    daemon = WatchDaemon(settings, lambda *a: None)
    assert daemon.run_cleanup() == []


def test_run_cleanup_moves_stale_files(tmp_path: Path):
    import os

    settings = _settings(tmp_path)
    settings.inbox_dir.mkdir(parents=True)
    old_file = settings.inbox_dir / "old.txt"
    old_file.write_bytes(b"x")
    old_time = time.time() - 10 * 86400
    os.utime(old_file, (old_time, old_time))

    daemon = WatchDaemon(settings, lambda *a: None)
    removed = daemon.run_cleanup()

    assert removed == [old_file]
    assert not old_file.exists()
