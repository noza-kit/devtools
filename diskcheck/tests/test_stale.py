from __future__ import annotations

import os
import time

from diskcheck.config import DEFAULT_STALE_EXTENSIONS, load_stale_extensions, normalize_extension
from diskcheck.stale import find_stale_files


def _set_atime(path, days_ago):
    now = time.time()
    target = now - days_ago * 86400
    os.utime(path, (target, target))


def test_normalize_extension_adds_dot_and_lowercases():
    assert normalize_extension("EXE") == ".exe"
    assert normalize_extension(".Dmg") == ".dmg"
    assert normalize_extension(" .msi ") == ".msi"


def test_load_stale_extensions_defaults_without_config():
    extensions = load_stale_extensions(None)
    assert ".exe" in extensions
    assert ".dmg" in extensions
    assert len(extensions) == len(DEFAULT_STALE_EXTENSIONS)


def test_load_stale_extensions_from_config_file(tmp_path):
    config_file = tmp_path / "diskcheck.yaml"
    config_file.write_text("extensions:\n  - .iso\n  - .zip\n", encoding="utf-8")

    extensions = load_stale_extensions(config_file)

    assert extensions == [".iso", ".zip"]


def test_find_stale_files_filters_by_extension_and_age(tmp_path):
    old_exe = tmp_path / "old_installer.exe"
    old_exe.write_bytes(b"x" * 100)
    _set_atime(old_exe, days_ago=200)

    recent_exe = tmp_path / "recent_installer.exe"
    recent_exe.write_bytes(b"x" * 100)
    _set_atime(recent_exe, days_ago=5)

    old_txt = tmp_path / "old_notes.txt"
    old_txt.write_bytes(b"x" * 100)
    _set_atime(old_txt, days_ago=200)

    results = find_stale_files(tmp_path, extensions=[".exe"], older_than_days=180)

    names = {f.path.name for f in results}
    assert names == {"old_installer.exe"}


def test_find_stale_files_sorted_by_size_descending(tmp_path):
    small = tmp_path / "small.exe"
    small.write_bytes(b"x" * 10)
    _set_atime(small, days_ago=200)

    big = tmp_path / "big.exe"
    big.write_bytes(b"x" * 1000)
    _set_atime(big, days_ago=200)

    results = find_stale_files(tmp_path, extensions=[".exe"], older_than_days=180)

    assert [f.path.name for f in results] == ["big.exe", "small.exe"]


def test_find_stale_files_extension_matching_is_case_insensitive(tmp_path):
    installer = tmp_path / "App.AppImage"
    installer.write_bytes(b"x" * 10)
    _set_atime(installer, days_ago=200)

    results = find_stale_files(tmp_path, extensions=[".appimage"], older_than_days=180)

    assert len(results) == 1
