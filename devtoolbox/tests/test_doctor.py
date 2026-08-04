import json

from typer.testing import CliRunner

import devtoolbox.doctor.collectors as collectors
from devtoolbox.doctor.cli import app
from devtoolbox.doctor.collectors import collect_python, collect_system, format_human

runner = CliRunner()


def test_collect_system_has_expected_keys():
    info = collect_system()
    for key in ("os", "system", "release", "machine", "hostname"):
        assert key in info
        assert info[key]


def test_collect_python_has_expected_keys():
    info = collect_python()
    assert info["version"]
    assert info["executable"]


def test_format_human_includes_present_sections():
    report = {
        "system": {"os": "TestOS"},
        "python": {"version": "3.12.0"},
        "hardware": {"logical_cores": 8},
        "gpu": ["Fake GPU 1"],
        "git": {"branch": "main", "commit": "abc123", "remote": None, "dirty": False},
    }
    text = format_human(report)
    assert "== System ==" in text
    assert "os: TestOS" in text
    assert "== GPU ==" in text
    assert "- Fake GPU 1" in text
    assert "== Git ==" in text
    assert "branch: main" in text


def test_format_human_marks_empty_gpu_list():
    report = {"system": {}, "python": {}, "hardware": {}, "gpu": []}
    text = format_human(report)
    assert "(none detected)" in text


def test_cli_json_output_is_valid_json():
    result = runner.invoke(app, ["--json", "--no-gpu"])
    assert result.exit_code == 0, result.output

    data = json.loads(result.output)
    assert "system" in data
    assert "python" in data
    assert "hardware" in data
    assert "gpu" not in data


def test_cli_writes_report_to_file(tmp_path):
    output_file = tmp_path / "report.txt"
    result = runner.invoke(app, ["--output", str(output_file), "--no-gpu"])
    assert result.exit_code == 0, result.output
    assert output_file.exists()
    assert "== System ==" in output_file.read_text(encoding="utf-8")


def test_cli_pip_flag_includes_pip_freeze(monkeypatch):
    monkeypatch.setattr(
        collectors, "collect_pip_freeze", lambda: ["fake-package==1.0.0"]
    )

    result = runner.invoke(app, ["--json", "--no-gpu", "--pip"])
    assert result.exit_code == 0, result.output

    data = json.loads(result.output)
    assert data["pip_freeze"] == ["fake-package==1.0.0"]
