from __future__ import annotations

import pytest

from tunelab.config import Config, ConfigError


def _base_raw(**overrides):
    raw = {
        "study": "demo",
        "direction": "minimize",
        "backend": "optuna",
        "budget": {"n_trials": 10},
        "space": {"x": {"type": "float", "low": 0.0, "high": 1.0}},
        "objective": {
            "mode": "command",
            "command": "python run.py --x {x} --result-file {result_file}",
            "result_file": "json",
        },
    }
    raw.update(overrides)
    return raw


def test_from_dict_builds_config():
    config = Config.from_dict(_base_raw())
    assert config.study == "demo"
    assert config.direction == "minimize"
    assert config.backend == "optuna"
    assert config.budget.n_trials == 10
    assert config.space.names == ["x"]
    assert config.objective.mode == "command"


def test_missing_study_raises():
    raw = _base_raw()
    del raw["study"]
    with pytest.raises(ConfigError):
        Config.from_dict(raw)


def test_invalid_direction_raises():
    with pytest.raises(ConfigError):
        Config.from_dict(_base_raw(direction="up"))


def test_invalid_backend_raises():
    with pytest.raises(ConfigError):
        Config.from_dict(_base_raw(backend="tensorflow"))


def test_missing_space_raises():
    raw = _base_raw()
    del raw["space"]
    with pytest.raises(ConfigError):
        Config.from_dict(raw)


def test_missing_objective_raises():
    raw = _base_raw()
    del raw["objective"]
    with pytest.raises(ConfigError):
        Config.from_dict(raw)


def test_command_objective_requires_result_file_or_regex():
    raw = _base_raw(objective={"mode": "command", "command": "echo hi"})
    with pytest.raises(ConfigError):
        Config.from_dict(raw)


def test_callable_objective_requires_entrypoint():
    raw = _base_raw(objective={"mode": "callable"})
    with pytest.raises(ConfigError):
        Config.from_dict(raw)


def test_callable_objective_ok_with_entrypoint():
    raw = _base_raw(objective={"mode": "callable", "entrypoint": "pkg.mod:func"})
    config = Config.from_dict(raw)
    assert config.objective.entrypoint == "pkg.mod:func"


def test_n_jobs_must_be_positive():
    raw = _base_raw(budget={"n_trials": 5, "n_jobs": 0})
    with pytest.raises(ConfigError):
        Config.from_dict(raw)


def test_budget_require_bound():
    raw = _base_raw(budget={})
    config = Config.from_dict(raw)
    with pytest.raises(ConfigError):
        config.budget.require_bound()


def test_load_from_yaml_file(tmp_path):
    path = tmp_path / "study.yaml"
    path.write_text(
        """
study: demo
space:
  x:
    type: float
    low: 0.0
    high: 1.0
objective:
  mode: command
  command: "python run.py --x {x} --result-file {result_file}"
  result_file: json
budget:
  n_trials: 3
""",
        encoding="utf-8",
    )
    config = Config.load(path)
    assert config.study == "demo"
    assert config.direction == "minimize"


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(ConfigError):
        Config.load(tmp_path / "nope.yaml")
