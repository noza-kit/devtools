from __future__ import annotations

import os

from claude_bridge.runtime_state import (
    RuntimeState,
    clear_runtime_state,
    is_process_alive,
    read_runtime_state,
    write_runtime_state,
)


def test_write_then_read_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    state = RuntimeState(pid=1234, started_at="2026-08-07T00:00:00Z", current="hobby: do it", queue_length=2)
    write_runtime_state(state, path)
    loaded = read_runtime_state(path)
    assert loaded == state


def test_read_missing_file_returns_none(tmp_path):
    assert read_runtime_state(tmp_path / "missing.json") is None


def test_read_corrupt_file_returns_none(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("not json", encoding="utf-8")
    assert read_runtime_state(path) is None


def test_clear_removes_file(tmp_path):
    path = tmp_path / "state.json"
    write_runtime_state(RuntimeState(pid=1, started_at="x", current=None, queue_length=0), path)
    clear_runtime_state(path)
    assert not path.exists()


def test_clear_missing_file_is_a_noop(tmp_path):
    clear_runtime_state(tmp_path / "missing.json")  # should not raise


def test_current_process_is_alive():
    assert is_process_alive(os.getpid()) is True


def test_unlikely_pid_is_not_alive():
    # PID 999999 essentially never exists on a real system.
    assert is_process_alive(999999) is False
