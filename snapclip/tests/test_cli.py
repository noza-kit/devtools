from pathlib import Path

import pytest
from typer.testing import CliRunner

from snapclip.cli import app

runner = CliRunner()


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "daemon" in result.output
    assert "history" in result.output
    assert "config" in result.output
    assert "web" in result.output


def test_daemon_help_does_not_start_the_daemon():
    result = runner.invoke(app, ["daemon", "--help"])
    assert result.exit_code == 0
    assert "start" in result.output


def test_config_show_default(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("snapclip.config.DEFAULT_CONFIG_PATH", tmp_path / "nonexistent.yaml")
    result = runner.invoke(app, ["config", "--show"])
    assert result.exit_code == 0
    assert "markdown" in result.output


def test_config_set_writes_file(monkeypatch, tmp_path: Path):
    cfg_path = tmp_path / "config.yaml"
    monkeypatch.setattr("snapclip.config.DEFAULT_CONFIG_PATH", cfg_path)
    result = runner.invoke(app, ["config", "--mode", "latex", "--img-dir", str(tmp_path / "figs")])
    assert result.exit_code == 0, result.output
    assert cfg_path.exists()
    assert "latex" in cfg_path.read_text(encoding="utf-8")


def test_config_invalid_mode_fails(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("snapclip.config.DEFAULT_CONFIG_PATH", tmp_path / "config.yaml")
    result = runner.invoke(app, ["config", "--mode", "html"])
    assert result.exit_code == 1


def test_web_command_calls_capture_full_page(monkeypatch, tmp_path: Path):
    calls = {}

    def fake_capture_full_page(url, output_path, viewport_width=1280):
        calls["url"] = url
        calls["output_path"] = output_path
        output_path.write_bytes(b"fake png bytes")
        return output_path

    monkeypatch.setattr("snapclip.cli.webcapture.capture_full_page", fake_capture_full_page)

    out = tmp_path / "page.png"
    result = runner.invoke(app, ["web", "https://example.com", "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert calls["url"] == "https://example.com"
    assert out.exists()


def test_web_command_missing_extra_reports_error(monkeypatch, tmp_path: Path):
    def raise_import_error(*a, **k):
        raise ImportError('Web capture requires the "web" extra')

    monkeypatch.setattr("snapclip.cli.webcapture.capture_full_page", raise_import_error)
    result = runner.invoke(app, ["web", "https://example.com", "-o", str(tmp_path / "out.png")])
    assert result.exit_code == 1
    assert "エラー" in result.output


def test_history_command_empty_history(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("snapclip.history.DEFAULT_DB_PATH", tmp_path / "h.db")
    monkeypatch.setattr("snapclip.history.DEFAULT_IMAGE_DIR", tmp_path / "himg")
    result = runner.invoke(app, ["history"])
    assert result.exit_code == 0, result.output
    assert "履歴がありません" in result.output
