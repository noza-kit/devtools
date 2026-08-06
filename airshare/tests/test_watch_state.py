import os
from pathlib import Path

from airshare.watch_state import (
    append_log_entry,
    is_process_alive,
    read_recent_log_entries,
    read_watch_runtime_info,
)


def test_is_process_alive_current_process():
    assert is_process_alive(os.getpid()) is True


def test_is_process_alive_bogus_pid():
    assert is_process_alive(999999) is False


def test_read_watch_runtime_info_missing_returns_none(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("airshare.watch_state.RUNTIME_DIR", tmp_path / "does-not-exist-dir")
    assert read_watch_runtime_info() is None


def test_append_and_read_log_entries(tmp_path: Path):
    log_path = tmp_path / "watch_log.jsonl"
    append_log_entry("受信しました", file_count=2, log_path=log_path)
    entries = read_recent_log_entries(within_hours=24, log_path=log_path)
    assert len(entries) == 1
    assert entries[0]["message"] == "受信しました"
    assert entries[0]["file_count"] == 2


def test_read_recent_log_entries_missing_file_returns_empty(tmp_path: Path):
    assert read_recent_log_entries(log_path=tmp_path / "missing.jsonl") == []


def test_read_recent_log_entries_excludes_old_entries(tmp_path: Path):
    import json
    from datetime import datetime, timedelta, timezone

    log_path = tmp_path / "watch_log.jsonl"
    old_entry = {
        "timestamp": (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat(),
        "message": "old",
        "file_count": 1,
    }
    log_path.write_text(json.dumps(old_entry) + "\n", encoding="utf-8")
    append_log_entry("new", file_count=1, log_path=log_path)

    entries = read_recent_log_entries(within_hours=24, log_path=log_path)
    assert len(entries) == 1
    assert entries[0]["message"] == "new"


def test_log_trims_to_max_entries(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("airshare.watch_state.MAX_LOG_ENTRIES", 5)
    log_path = tmp_path / "watch_log.jsonl"
    for i in range(10):
        append_log_entry(f"entry {i}", file_count=1, log_path=log_path)

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5


def test_read_recent_log_entries_skips_malformed_lines(tmp_path: Path):
    log_path = tmp_path / "watch_log.jsonl"
    log_path.write_text("not valid json\n", encoding="utf-8")
    append_log_entry("valid", file_count=1, log_path=log_path)
    entries = read_recent_log_entries(log_path=log_path)
    assert len(entries) == 1
