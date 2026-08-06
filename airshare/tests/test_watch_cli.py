from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from airshare.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_watch_state(tmp_path: Path, monkeypatch):
    """Every watch_state read/write goes through a tmp_path-scoped
    RUNTIME_DIR instead of the real ~/.airshare, so CLI tests don't
    touch (or get confused by) this machine's actual state."""
    runtime_dir = tmp_path / ".airshare_state"
    monkeypatch.setattr("airshare.watch_state.RUNTIME_DIR", runtime_dir)
    return runtime_dir


def test_watch_clean_no_config_uses_airshare_receive_dir(tmp_path: Path, monkeypatch):
    receive_dir = tmp_path / "received"
    receive_dir.mkdir()
    monkeypatch.setattr("airshare.cli.load_settings", lambda **k: type("S", (), {"receive_dir": receive_dir})())

    result = runner.invoke(app, ["watch", "clean", "--force"])
    assert result.exit_code == 0, result.output
    assert "ありません" in result.output


def test_watch_clean_missing_config_fails(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("airshare.cli.load_settings", lambda **k: type("S", (), {"receive_dir": tmp_path})())
    result = runner.invoke(app, ["watch", "clean", "--config", str(tmp_path / "missing.yaml")])
    assert result.exit_code == 1


def test_watch_clean_cleanup_disabled(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("airshare.cli.load_settings", lambda **k: type("S", (), {"receive_dir": tmp_path})())
    cfg = tmp_path / "watch.yaml"
    cfg.write_text("cleanup:\n  enabled: false\n", encoding="utf-8")

    result = runner.invoke(app, ["watch", "clean", "--config", str(cfg)])
    assert result.exit_code == 0, result.output
    assert "無効化" in result.output


def test_watch_clean_removes_stale_files_with_force(tmp_path: Path, monkeypatch):
    import os
    import time

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    old_file = inbox / "old.txt"
    old_file.write_bytes(b"x")
    old_time = time.time() - 10 * 86400
    os.utime(old_file, (old_time, old_time))

    monkeypatch.setattr("airshare.cli.load_settings", lambda **k: type("S", (), {"receive_dir": inbox})())
    cfg = tmp_path / "watch.yaml"
    cfg.write_text(f"inbox_dir: {inbox.as_posix()!r}\ncleanup:\n  expire_days: 7\n", encoding="utf-8")

    result = runner.invoke(app, ["watch", "clean", "--config", str(cfg), "--force"])
    assert result.exit_code == 0, result.output
    assert not old_file.exists()


def test_watch_status_not_running(tmp_path: Path):
    result = runner.invoke(app, ["watch", "status"])
    assert result.exit_code == 0, result.output
    assert "停止中" in result.output


def test_watch_status_running(monkeypatch, isolated_watch_state: Path):
    from airshare.watch_state import write_watch_runtime_info

    write_watch_runtime_info()
    result = runner.invoke(app, ["watch", "status"])
    assert result.exit_code == 0, result.output
    assert "稼働中" in result.output


def test_watch_status_shows_recent_activity(isolated_watch_state: Path):
    from airshare.watch_state import append_log_entry

    append_log_entry("3件のファイルを受信しました", file_count=3)
    result = runner.invoke(app, ["watch", "status"])
    assert result.exit_code == 0, result.output
    assert "3件のファイルを受信しました" in result.output


def test_watch_status_no_activity_message(tmp_path: Path):
    result = runner.invoke(app, ["watch", "status"])
    assert "受信履歴はありません" in result.output


def test_watch_start_help():
    result = runner.invoke(app, ["watch", "start", "--help"])
    assert result.exit_code == 0
    assert "interval" in result.output.lower()
