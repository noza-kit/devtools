from __future__ import annotations

from types import SimpleNamespace

from kanbancli.autostart import AutostartError, build_run_command, register_autostart, remove_autostart
import pytest


def _completed(returncode: int, stderr: str = "", stdout: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stderr=stderr, stdout=stdout)


def test_build_run_command_includes_options(monkeypatch, tmp_path):
    monkeypatch.setattr("kanbancli.autostart.resolve_kanbancli_command", lambda: "kanbancli")
    file_path = tmp_path / ".kanban.md"

    command = build_run_command(within_days=5, channels=["desktop", "slack"], file=file_path)

    assert command.startswith("kanbancli remind")
    assert "--within-days 5" in command
    assert "--channels desktop,slack" in command
    assert f'--file "{file_path}"' in command


def test_register_autostart_uses_daily_trigger(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _completed(0)

    monkeypatch.setattr("kanbancli.autostart.subprocess.run", fake_run)
    monkeypatch.setattr("kanbancli.autostart.resolve_kanbancli_command", lambda: "kanbancli")

    register_autostart(task_name="KanbancliTest", start_time="08:30")

    cmd = captured["cmd"]
    assert cmd[0] == "schtasks"
    assert "/create" in cmd
    assert "DAILY" in cmd
    assert "08:30" in cmd
    assert "KanbancliTest" in cmd
    assert "/f" in cmd


def test_register_autostart_raises_on_failure(monkeypatch):
    monkeypatch.setattr("kanbancli.autostart.subprocess.run", lambda cmd, **k: _completed(1, stderr="denied"))
    monkeypatch.setattr("kanbancli.autostart.resolve_kanbancli_command", lambda: "kanbancli")

    with pytest.raises(AutostartError, match="denied"):
        register_autostart()


def test_remove_autostart_success(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _completed(0)

    monkeypatch.setattr("kanbancli.autostart.subprocess.run", fake_run)
    remove_autostart(task_name="KanbancliTest")

    assert captured["cmd"] == ["schtasks", "/delete", "/tn", "KanbancliTest", "/f"]


def test_remove_autostart_missing_task_is_not_an_error(monkeypatch):
    monkeypatch.setattr(
        "kanbancli.autostart.subprocess.run",
        lambda cmd, **k: _completed(1, stderr="ERROR: The system cannot find the file specified."),
    )
    remove_autostart(task_name="NeverRegistered")  # should not raise


def test_remove_autostart_other_failure_raises(monkeypatch):
    monkeypatch.setattr("kanbancli.autostart.subprocess.run", lambda cmd, **k: _completed(1, stderr="access denied"))
    with pytest.raises(AutostartError):
        remove_autostart(task_name="KanbancliTest")
