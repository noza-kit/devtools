from __future__ import annotations

import optuna
import pytest

from tunelab.backends import optuna_backend, random_backend
from tunelab.config import Budget, Config, ConfigError, ObjectiveSpec
from tunelab.objective.errors import TrialFailed
from tunelab.space import SearchSpace


def _config(backend: str, n_trials=8, n_jobs=1, timeout=None, direction="minimize") -> Config:
    space = SearchSpace.from_dict({"x": {"type": "float", "low": 0.0, "high": 10.0}})
    objective = ObjectiveSpec(mode="callable", entrypoint="unused:unused")
    budget = Budget(n_trials=n_trials, timeout=timeout, n_jobs=n_jobs)
    return Config(study="test", direction=direction, backend=backend, budget=budget, space=space, objective=objective)


def quadratic(params):
    return (params["x"] - 3.0) ** 2


@pytest.fixture
def study():
    return optuna.create_study(direction="minimize")


def test_optuna_backend_records_all_trials(study, monkeypatch):
    config = _config("optuna", n_trials=6)
    monkeypatch.setattr(optuna_backend, "evaluate", lambda spec, params: quadratic(params))
    optuna_backend.run(study, config)
    assert len(study.trials) == 6
    assert all(t.state == optuna.trial.TrialState.COMPLETE for t in study.trials)


def test_optuna_backend_records_failed_trials_without_aborting(study, monkeypatch):
    def flaky(spec, params):
        if params["x"] > 5.0:
            raise TrialFailed("x too large")
        return quadratic(params)

    config = _config("optuna", n_trials=10)
    monkeypatch.setattr(optuna_backend, "evaluate", flaky)
    optuna_backend.run(study, config)
    assert len(study.trials) == 10
    states = {t.state for t in study.trials}
    assert states <= {optuna.trial.TrialState.COMPLETE, optuna.trial.TrialState.FAIL}


def test_optuna_backend_requires_bound(study):
    config = _config("optuna", n_trials=None)
    with pytest.raises(ConfigError):
        optuna_backend.run(study, config)


def test_random_backend_records_expected_count(study, monkeypatch):
    config = _config("random", n_trials=7, n_jobs=2)
    monkeypatch.setattr(random_backend, "evaluate", lambda spec, params: quadratic(params))
    random_backend.run_random(study, config)
    assert len(study.trials) == 7
    assert all(t.state == optuna.trial.TrialState.COMPLETE for t in study.trials)


def test_random_backend_records_failures(study, monkeypatch):
    def always_fails(spec, params):
        raise TrialFailed("nope")

    config = _config("random", n_trials=3)
    monkeypatch.setattr(random_backend, "evaluate", always_fails)
    random_backend.run_random(study, config)
    assert len(study.trials) == 3
    assert all(t.state == optuna.trial.TrialState.FAIL for t in study.trials)


def test_random_backend_requires_bound(study):
    config = _config("random", n_trials=None)
    with pytest.raises(ConfigError):
        random_backend.run_random(study, config)


def test_grid_backend_enumerates_full_grid(study, monkeypatch):
    space = SearchSpace.from_dict({"n": {"type": "int", "low": 0, "high": 4, "step": 2}})
    objective = ObjectiveSpec(mode="callable", entrypoint="unused:unused")
    config = Config(
        study="grid-test", direction="minimize", backend="grid",
        budget=Budget(n_jobs=1), space=space, objective=objective,
    )
    monkeypatch.setattr(random_backend, "evaluate", lambda spec, params: float(params["n"]))
    random_backend.run_grid(study, config)
    assert sorted(t.params["n"] for t in study.trials) == [0, 2, 4]


def test_grid_backend_respects_n_trials_cap(study, monkeypatch):
    space = SearchSpace.from_dict({"n": {"type": "int", "low": 0, "high": 4, "step": 2}})
    objective = ObjectiveSpec(mode="callable", entrypoint="unused:unused")
    config = Config(
        study="grid-test", direction="minimize", backend="grid",
        budget=Budget(n_trials=2, n_jobs=1), space=space, objective=objective,
    )
    monkeypatch.setattr(random_backend, "evaluate", lambda spec, params: float(params["n"]))
    random_backend.run_grid(study, config)
    assert len(study.trials) == 2
