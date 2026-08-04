from __future__ import annotations

import sys

import pytest

from tunelab.config import ObjectiveSpec
from tunelab.objective.command import run_command_objective
from tunelab.objective.errors import ObjectiveError, TrialFailed


def _spec(command: str, **kwargs) -> ObjectiveSpec:
    return ObjectiveSpec(mode="command", command=command, result_file=kwargs.pop("result_file", "json"), **kwargs)


def test_result_file_mode_returns_value(quadratic_script):
    command = f'"{sys.executable}" "{quadratic_script}" --x {{x}} --result-file {{result_file}}'
    spec = _spec(command)
    value = run_command_objective(spec, {"x": 5.0})
    assert value == pytest.approx(4.0)


def test_result_regex_mode_parses_stdout(tmp_path):
    script = tmp_path / "print_value.py"
    script.write_text("import sys\nprint(f'score: {float(sys.argv[1]) ** 2}')\n", encoding="utf-8")
    command = f'"{sys.executable}" "{script}" {{x}}'
    spec = ObjectiveSpec(mode="command", command=command, result_regex=r"score:\s*([0-9.]+)")
    value = run_command_objective(spec, {"x": 3.0})
    assert value == pytest.approx(9.0)


def test_nonzero_exit_raises_trial_failed(tmp_path):
    script = tmp_path / "fail.py"
    script.write_text("import sys\nsys.exit(1)\n", encoding="utf-8")
    command = f'"{sys.executable}" "{script}"'
    spec = ObjectiveSpec(mode="command", command=command, result_regex=r"(\d+)")
    with pytest.raises(TrialFailed):
        run_command_objective(spec, {})


def test_missing_result_file_raises_trial_failed(tmp_path):
    script = tmp_path / "noop.py"
    script.write_text("pass\n", encoding="utf-8")
    command = f'"{sys.executable}" "{script}"'
    spec = _spec(command)
    with pytest.raises(TrialFailed):
        run_command_objective(spec, {})


def test_unmatched_regex_raises_trial_failed(tmp_path):
    script = tmp_path / "print_nothing.py"
    script.write_text("print('nothing useful')\n", encoding="utf-8")
    command = f'"{sys.executable}" "{script}"'
    spec = ObjectiveSpec(mode="command", command=command, result_regex=r"score:\s*([0-9.]+)")
    with pytest.raises(TrialFailed):
        run_command_objective(spec, {})


def test_unknown_placeholder_raises_objective_error(quadratic_script):
    command = f'"{sys.executable}" "{quadratic_script}" --x {{missing_param}} --result-file {{result_file}}'
    spec = _spec(command)
    with pytest.raises(ObjectiveError):
        run_command_objective(spec, {"x": 1.0})


def test_timeout_raises_trial_failed(tmp_path):
    script = tmp_path / "slow.py"
    script.write_text("import time\ntime.sleep(5)\n", encoding="utf-8")
    command = f'"{sys.executable}" "{script}"'
    spec = ObjectiveSpec(mode="command", command=command, result_regex=r"(\d+)", timeout_per_trial=0.2)
    with pytest.raises(TrialFailed):
        run_command_objective(spec, {})
