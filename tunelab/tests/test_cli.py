from __future__ import annotations

import sys

from typer.testing import CliRunner

from tunelab.cli import app

runner = CliRunner()


def _write_config(tmp_path, quadratic_script, **overrides):
    command_line = f'"{sys.executable}" "{quadratic_script}" --x {{x}} --result-file {{result_file}}'
    n_trials = overrides.get("n_trials", 5)
    n_jobs = overrides.get("n_jobs", 1)
    backend = overrides.get("backend", "random")
    config_text = f"""\
study: demo
direction: minimize
backend: {backend}
budget:
  n_trials: {n_trials}
  n_jobs: {n_jobs}
space:
  x:
    type: float
    low: 0.0
    high: 10.0
objective:
  mode: command
  command: '{command_line}'
  result_file: json
"""
    path = tmp_path / "demo.yaml"
    path.write_text(config_text, encoding="utf-8")
    return path


def test_init_writes_template(tmp_path):
    output = tmp_path / "new-study.yaml"
    result = runner.invoke(app, ["init", "new-study", "--output", str(output)])
    assert result.exit_code == 0, result.output
    assert output.exists()
    assert "study: new-study" in output.read_text(encoding="utf-8")


def test_init_refuses_to_overwrite_without_force(tmp_path):
    output = tmp_path / "existing.yaml"
    output.write_text("study: existing\n", encoding="utf-8")
    result = runner.invoke(app, ["init", "existing", "--output", str(output)])
    assert result.exit_code != 0


def test_run_then_status_best_list_export(tmp_path, tunelab_home, quadratic_script):
    config_path = _write_config(tmp_path, quadratic_script, n_trials=5)

    run_result = runner.invoke(app, ["run", str(config_path)])
    assert run_result.exit_code == 0, run_result.output
    assert "Finished." in run_result.output

    status_result = runner.invoke(app, ["status", "demo"])
    assert status_result.exit_code == 0
    assert "trials: 5" in status_result.output

    best_result = runner.invoke(app, ["best", "demo", "--top", "3"])
    assert best_result.exit_code == 0
    assert "value=" in best_result.output

    list_result = runner.invoke(app, ["list", "demo"])
    assert list_result.exit_code == 0
    assert "#0" in list_result.output

    csv_path = tmp_path / "out.csv"
    export_result = runner.invoke(app, ["export", "demo", "--output", str(csv_path)])
    assert export_result.exit_code == 0
    assert csv_path.exists()
    assert len(csv_path.read_text(encoding="utf-8").strip().splitlines()) == 6  # header + 5 trials

    studies_result = runner.invoke(app, ["studies"])
    assert "demo" in studies_result.output


def test_run_resumes_by_default(tmp_path, tunelab_home, quadratic_script):
    config_path = _write_config(tmp_path, quadratic_script, n_trials=3)
    runner.invoke(app, ["run", str(config_path)])
    second = runner.invoke(app, ["run", str(config_path)])
    assert second.exit_code == 0
    status_result = runner.invoke(app, ["status", "demo"])
    assert "trials: 6" in status_result.output


def test_run_fresh_discards_previous_trials(tmp_path, tunelab_home, quadratic_script):
    config_path = _write_config(tmp_path, quadratic_script, n_trials=3)
    runner.invoke(app, ["run", str(config_path)])
    second = runner.invoke(app, ["run", str(config_path), "--fresh"])
    assert second.exit_code == 0
    status_result = runner.invoke(app, ["status", "demo"])
    assert "trials: 3" in status_result.output


def test_status_missing_study_errors(tunelab_home):
    result = runner.invoke(app, ["status", "nope"])
    assert result.exit_code != 0


def test_delete_study(tmp_path, tunelab_home, quadratic_script):
    config_path = _write_config(tmp_path, quadratic_script, n_trials=2)
    runner.invoke(app, ["run", str(config_path)])
    result = runner.invoke(app, ["delete", "demo", "--yes"])
    assert result.exit_code == 0
    status_result = runner.invoke(app, ["status", "demo"])
    assert status_result.exit_code != 0


def test_run_with_grid_backend(tmp_path, tunelab_home, quadratic_script):
    config_path = _write_config(tmp_path, quadratic_script, backend="grid")
    # grid backend needs a discrete space; override with an int param instead.
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "space:\n  x:\n    type: float\n    low: 0.0\n    high: 10.0\n",
            "space:\n  x:\n    type: int\n    low: 0\n    high: 4\n    step: 1\n",
        ),
        encoding="utf-8",
    )
    result = runner.invoke(app, ["run", str(config_path)])
    assert result.exit_code == 0, result.output
    status_result = runner.invoke(app, ["status", "demo"])
    assert "trials: 5" in status_result.output
