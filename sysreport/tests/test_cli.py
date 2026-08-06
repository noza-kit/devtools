from __future__ import annotations

import json

from typer.testing import CliRunner

from sysreport.cli import app

runner = CliRunner()


def test_run_dry_run_prints_report_and_skips_notify(fake_disk, fake_hardware, monkeypatch):
    calls = []
    monkeypatch.setattr("sysreport.cli.notify", lambda message, channels, **kw: calls.append((message, channels)))

    result = runner.invoke(app, ["run", "--dry-run", "--cpu-interval", "0"])

    assert result.exit_code == 0, result.output
    assert "💾" in result.output
    assert calls == []


def test_run_sends_notification_with_formatted_text(fake_disk, fake_hardware, monkeypatch):
    calls = []

    def fake_notify(message, channels, **kw):
        calls.append((message, channels))
        return {}

    monkeypatch.setattr("sysreport.cli.notify", fake_notify)

    result = runner.invoke(app, ["run", "--channels", "desktop,discord", "--cpu-interval", "0"])

    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    message, channels = calls[0]
    assert "🖥️" in message
    assert channels == ["desktop", "discord"]


def test_run_json_output_is_valid_json(fake_disk, fake_hardware, monkeypatch):
    monkeypatch.setattr("sysreport.cli.notify", lambda message, channels, **kw: {})

    result_lines = runner.invoke(app, ["run", "--json", "--dry-run", "--cpu-interval", "0"])

    assert result_lines.exit_code == 0, result_lines.output
    data = json.loads(result_lines.output)
    assert "drives" in data and "cpu" in data and "memory" in data


def test_run_highlight_warnings_marks_low_storage(fake_disk, fake_hardware, monkeypatch):
    monkeypatch.setattr("sysreport.cli.notify", lambda message, channels, **kw: {})

    result = runner.invoke(
        app,
        ["run", "--dry-run", "--highlight-warnings", "--storage-min-percent", "50", "--cpu-interval", "0"],
    )

    assert result.exit_code == 0, result.output
    assert "⚠️" in result.output


def test_run_reports_failed_channels(fake_disk, fake_hardware, monkeypatch):
    from notify import ChannelResult

    monkeypatch.setattr(
        "sysreport.cli.notify",
        lambda message, channels, **kw: {"slack": ChannelResult("slack", False, "boom")},
    )

    result = runner.invoke(app, ["run", "--channels", "slack", "--cpu-interval", "0"])

    assert result.exit_code == 0, result.output
    assert "slack" in result.output.lower()


def test_run_invalid_config_path_fails(fake_disk, fake_hardware, tmp_path):
    result = runner.invoke(app, ["run", "--config", str(tmp_path / "missing.yaml"), "--cpu-interval", "0"])

    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_setup_autostart_registers_task(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "sysreport.cli.register_autostart",
        lambda **kw: calls.append(kw),
    )

    result = runner.invoke(app, ["setup-autostart", "--channels", "desktop"])

    assert result.exit_code == 0, result.output
    assert "registered" in result.output.lower()
    assert calls[0]["channels"] == ["desktop"]


def test_setup_autostart_remove_flag_removes_task(monkeypatch):
    calls = []
    monkeypatch.setattr("sysreport.cli.remove_autostart", lambda **kw: calls.append(kw))

    result = runner.invoke(app, ["setup-autostart", "--remove"])

    assert result.exit_code == 0, result.output
    assert "removed" in result.output.lower()
    assert len(calls) == 1


def test_setup_autostart_failure_reports_error(monkeypatch):
    from sysreport.autostart import AutostartError

    def boom(**kw):
        raise AutostartError("schtasks not available")

    monkeypatch.setattr("sysreport.cli.register_autostart", boom)

    result = runner.invoke(app, ["setup-autostart"])

    assert result.exit_code == 1
    assert "schtasks not available" in result.output
