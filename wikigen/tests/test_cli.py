from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from wikigen.cli import app

runner = CliRunner()


def test_build_command_writes_site(sample_source: Path, tmp_path: Path):
    output = tmp_path / "out"
    result = runner.invoke(app, ["build", str(sample_source), "--output", str(output)])

    assert result.exit_code == 0, result.output
    assert "Built 3 page(s)" in result.output
    assert (output / "index.html").exists()


def test_build_command_reports_missing_source(tmp_path: Path):
    result = runner.invoke(app, ["build", str(tmp_path / "nope"), "--output", str(tmp_path / "out")])
    assert result.exit_code != 0


def test_build_command_reports_empty_source(tmp_path: Path):
    source = tmp_path / "empty"
    source.mkdir()
    result = runner.invoke(app, ["build", str(source), "--output", str(tmp_path / "out")])
    assert result.exit_code != 0


def test_serve_command_reports_missing_directory(tmp_path: Path):
    result = runner.invoke(app, ["serve", str(tmp_path / "nope")])
    assert result.exit_code != 0
    assert "run 'wikigen build' first" in result.output
