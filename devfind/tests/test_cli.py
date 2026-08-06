from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from devfind.cli import app
from devfind.config import Settings
from devfind.tools import MissingToolError

runner = CliRunner()


def _patch_pipeline(monkeypatch, *, fd=None, rg=None, selected=None):
    monkeypatch.setattr("devfind.cli.ensure_required_tools", lambda: None)
    monkeypatch.setattr(
        "devfind.cli.load_settings",
        lambda config: Settings(target_dirs=[Path("/downloads")], exclude=["venv"]),
    )
    monkeypatch.setattr("devfind.cli.run_fd", lambda keyword, target_dirs, exclude: fd or [])
    monkeypatch.setattr("devfind.cli.run_rg", lambda keyword, target_dirs, exclude: rg or [])
    monkeypatch.setattr("devfind.cli.run_fzf", lambda matches: selected)


def test_cli_prints_selected_path(monkeypatch):
    _patch_pipeline(monkeypatch, fd=["a/one.txt"], rg=["a/two.txt"], selected="a/two.txt")

    result = runner.invoke(app, ["keyword"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "a/two.txt"


def test_cli_exits_1_when_missing_tools(monkeypatch):
    def _raise():
        raise MissingToolError(["fd"])

    monkeypatch.setattr("devfind.cli.ensure_required_tools", _raise)

    result = runner.invoke(app, ["keyword"])

    assert result.exit_code == 1
    assert "fd" in result.output


def test_cli_exits_1_when_no_matches(monkeypatch):
    _patch_pipeline(monkeypatch, fd=[], rg=[], selected=None)

    result = runner.invoke(app, ["keyword"])

    assert result.exit_code == 1
    assert "見つかりませんでした" in result.output


def test_cli_exits_130_when_selection_cancelled(monkeypatch):
    _patch_pipeline(monkeypatch, fd=["a/one.txt"], rg=[], selected=None)

    result = runner.invoke(app, ["keyword"])

    assert result.exit_code == 130
    assert result.stdout.strip() == ""


def test_cli_passes_explicit_config_path(monkeypatch, tmp_path):
    captured = {}

    monkeypatch.setattr("devfind.cli.ensure_required_tools", lambda: None)

    def fake_load_settings(config):
        captured["config"] = config
        return Settings(target_dirs=[Path("/downloads")], exclude=[])

    monkeypatch.setattr("devfind.cli.load_settings", fake_load_settings)
    monkeypatch.setattr("devfind.cli.run_fd", lambda keyword, target_dirs, exclude: ["a.txt"])
    monkeypatch.setattr("devfind.cli.run_rg", lambda keyword, target_dirs, exclude: [])
    monkeypatch.setattr("devfind.cli.run_fzf", lambda matches: "a.txt")

    config_file = tmp_path / "custom.yaml"
    result = runner.invoke(app, ["keyword", "--config", str(config_file)])

    assert result.exit_code == 0
    assert captured["config"] == config_file
