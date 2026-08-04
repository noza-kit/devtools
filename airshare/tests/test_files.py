from __future__ import annotations

from pathlib import Path

import pytest

from airshare.files import list_files, resolve_download_path, save_upload


def test_list_files_sorts_newest_first(tmp_path: Path) -> None:
    old = tmp_path / "old.txt"
    new = tmp_path / "new.txt"
    old.write_text("a")
    new.write_text("b")
    import os
    import time

    now = time.time()
    os.utime(old, (now - 100, now - 100))
    os.utime(new, (now, now))

    entries = list_files(tmp_path)
    assert [e.name for e in entries] == ["new.txt", "old.txt"]


def test_list_files_ignores_directories(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "file.txt").write_text("x")

    entries = list_files(tmp_path)
    assert [e.name for e in entries] == ["file.txt"]


def test_resolve_download_path_returns_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "report.pdf"
    target.write_bytes(b"%PDF-1.4")

    resolved = resolve_download_path(tmp_path, "report.pdf")
    assert resolved == target


def test_resolve_download_path_blocks_traversal(tmp_path: Path) -> None:
    outside = tmp_path.parent / "secret.txt"
    outside.write_text("nope")
    try:
        # "../secret.txt" is reduced to its basename "secret.txt", which does not
        # exist inside `tmp_path` itself, so this must not resolve to the file
        # sitting one directory up.
        with pytest.raises(FileNotFoundError):
            resolve_download_path(tmp_path, "../secret.txt")
    finally:
        outside.unlink()


def test_resolve_download_path_rejects_dotdot_only(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        resolve_download_path(tmp_path, "..")


def test_resolve_download_path_missing_file_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        resolve_download_path(tmp_path, "missing.txt")


def test_save_upload_writes_content(tmp_path: Path) -> None:
    saved = save_upload(tmp_path, "photo.jpg", b"binarydata")
    assert saved.read_bytes() == b"binarydata"
    assert saved.parent == tmp_path


def test_save_upload_avoids_collision(tmp_path: Path) -> None:
    first = save_upload(tmp_path, "photo.jpg", b"one")
    second = save_upload(tmp_path, "photo.jpg", b"two")

    assert first.name == "photo.jpg"
    assert second.name == "photo (1).jpg"
    assert first.read_bytes() == b"one"
    assert second.read_bytes() == b"two"


def test_save_upload_sanitizes_path_traversal(tmp_path: Path) -> None:
    saved = save_upload(tmp_path, "../../evil.txt", b"x")
    assert saved.parent == tmp_path
    assert saved.name == "evil.txt"
