import os
import time
from pathlib import Path

from airshare.watch_cleanup import find_stale_files, move_to_trash


def _touch_with_atime(path: Path, atime: float) -> None:
    path.write_bytes(b"data")
    os.utime(path, (atime, path.stat().st_mtime))


def test_find_stale_files_respects_expire_days(tmp_path: Path):
    now = time.time()
    old_file = tmp_path / "old.jpg"
    new_file = tmp_path / "new.jpg"
    _touch_with_atime(old_file, now - 10 * 86400)
    _touch_with_atime(new_file, now - 1 * 86400)

    stale = find_stale_files([tmp_path], expire_days=7, now=now)

    assert old_file in stale
    assert new_file not in stale


def test_find_stale_files_missing_directory_is_skipped(tmp_path: Path):
    assert find_stale_files([tmp_path / "does-not-exist"], expire_days=7) == []


def test_find_stale_files_ignores_subdirectories_non_recursive(tmp_path: Path):
    now = time.time()
    subdir = tmp_path / "sub"
    subdir.mkdir()
    nested = subdir / "old.jpg"
    _touch_with_atime(nested, now - 10 * 86400)

    stale = find_stale_files([tmp_path], expire_days=7, now=now)
    assert stale == []  # non-recursive: nested file isn't found


def test_find_stale_files_multiple_directories(tmp_path: Path):
    now = time.time()
    dir_a, dir_b = tmp_path / "a", tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()
    old_a = dir_a / "old.jpg"
    old_b = dir_b / "old.pdf"
    _touch_with_atime(old_a, now - 10 * 86400)
    _touch_with_atime(old_b, now - 10 * 86400)

    stale = find_stale_files([dir_a, dir_b], expire_days=7, now=now)
    assert set(stale) == {old_a, old_b}


def test_move_to_trash_removes_file(tmp_path: Path):
    target = tmp_path / "file.jpg"
    target.write_bytes(b"data")
    move_to_trash(target)
    assert not target.exists()


def test_move_to_trash_falls_back_to_delete_without_send2trash(tmp_path: Path, monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "send2trash":
            raise ImportError("no send2trash")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    target = tmp_path / "file.jpg"
    target.write_bytes(b"data")
    move_to_trash(target)
    assert not target.exists()
