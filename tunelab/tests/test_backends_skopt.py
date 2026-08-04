from __future__ import annotations

import optuna
import pytest

pytest.importorskip("skopt")

from tunelab.backends import skopt_backend  # noqa: E402
from tunelab.config import Budget, Config, ObjectiveSpec  # noqa: E402
from tunelab.space import SearchSpace  # noqa: E402


def quadratic(params):
    return (params["x"] - 3.0) ** 2


def test_skopt_backend_records_all_trials(monkeypatch):
    space = SearchSpace.from_dict({"x": {"type": "float", "low": 0.0, "high": 10.0}})
    objective = ObjectiveSpec(mode="callable", entrypoint="unused:unused")
    config = Config(
        study="skopt-test", direction="minimize", backend="skopt",
        budget=Budget(n_trials=5), space=space, objective=objective,
    )
    monkeypatch.setattr(skopt_backend, "evaluate", lambda spec, params: quadratic(params))

    study = optuna.create_study(direction="minimize")
    skopt_backend.run(study, config)

    assert len(study.trials) == 5
    assert all(t.state == optuna.trial.TrialState.COMPLETE for t in study.trials)


def test_skopt_backend_snaps_stepped_int_params(monkeypatch):
    space = SearchSpace.from_dict({"batch_size": {"type": "int", "low": 16, "high": 256, "step": 16}})
    objective = ObjectiveSpec(mode="callable", entrypoint="unused:unused")
    config = Config(
        study="skopt-int-test", direction="minimize", backend="skopt",
        budget=Budget(n_trials=10), space=space, objective=objective,
    )
    monkeypatch.setattr(skopt_backend, "evaluate", lambda spec, params: float(params["batch_size"]))

    study = optuna.create_study(direction="minimize")
    skopt_backend.run(study, config)

    assert len(study.trials) == 10
    assert all(t.state == optuna.trial.TrialState.COMPLETE for t in study.trials)
    assert all(t.params["batch_size"] % 16 == 0 for t in study.trials)
