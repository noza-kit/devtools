from __future__ import annotations

from types import SimpleNamespace

import pytest

from sysreport.autostart import AutostartError, build_run_command, register_autostart, remove_autostart


def _completed(returncode: int, stderr: str = "", stdout: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stderr=stderr, stdout=stdout)


def test_build_run_command_includes_channels_and_flags(monkeypatch, tmp_path):
    monkeypatch.setattr("sysreport.autostart.resolve_sysreport_command", lambda: "sysreport")
    config_path = tmp_path / "thresholds.yaml"

    command = build_run_command(channels=["desktop", "slack"], config=config_path, highlight_warnings=True)

    assert command.startswith("sysreport run")
    assert "--channels desktop,slack" in command
    assert f'--config "{config_path}"' in command
    assert "--highlight-warnings" in command


def test_register_autostart_invokes_schtasks_with_onlogon_trigger(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _completed(0)

    monkeypatch.setattr("sysreport.autostart.subprocess.run", fake_run)
    monkeypatch.setattr("sysreport.autostart.resolve_sysreport_command", lambda: "sysreport")

    register_autostart(task_name="SysReportTest", channels=["desktop"])

    cmd = captured["cmd"]
    assert cmd[0] == "schtasks"
    assert "/create" in cmd
    assert "ONLOGON" in cmd
    assert "SysReportTest" in cmd


def test_register_autostart_raises_on_failure(monkeypatch):
    monkeypatch.setattr(
        "sysreport.autostart.subprocess.run", lambda cmd, **kw: _completed(1, stderr="access denied")
    )

    with pytest.raises(AutostartError, match="access denied"):
        register_autostart()


def test_remove_autostart_invokes_schtasks_delete(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _completed(0)

    monkeypatch.setattr("sysreport.autostart.subprocess.run", fake_run)

    remove_autostart(task_name="SysReportTest")

    cmd = captured["cmd"]
    assert cmd == ["schtasks", "/delete", "/tn", "SysReportTest", "/f"]


def test_remove_autostart_missing_task_is_not_an_error(monkeypatch):
    monkeypatch.setattr(
        "sysreport.autostart.subprocess.run",
        lambda cmd, **kw: _completed(1, stderr="ERROR: The system cannot find the file specified."),
    )

    remove_autostart(task_name="DoesNotExist")  # should not raise


def test_remove_autostart_other_failure_raises(monkeypatch):
    monkeypatch.setattr(
        "sysreport.autostart.subprocess.run", lambda cmd, **kw: _completed(1, stderr="access denied")
    )

    with pytest.raises(AutostartError, match="access denied"):
        remove_autostart()
