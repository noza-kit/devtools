from __future__ import annotations

import numpy as np
import optuna
import pytest

from tunelab.space import CategoricalParam, FloatParam, IntParam, SearchSpace, SearchSpaceError


def test_from_dict_builds_expected_param_types():
    space = SearchSpace.from_dict(
        {
            "lr": {"type": "float", "low": 1e-5, "high": 1e-1, "log": True},
            "batch_size": {"type": "int", "low": 16, "high": 256, "step": 16},
            "optimizer": {"type": "categorical", "choices": ["adam", "sgd"]},
        }
    )
    assert space.names == ["lr", "batch_size", "optimizer"]
    assert isinstance(space.params[0], FloatParam)
    assert isinstance(space.params[1], IntParam)
    assert isinstance(space.params[2], CategoricalParam)


def test_unknown_type_raises():
    with pytest.raises(SearchSpaceError):
        SearchSpace.from_dict({"x": {"type": "bogus", "low": 0, "high": 1}})


def test_empty_space_raises():
    with pytest.raises(SearchSpaceError):
        SearchSpace.from_dict({})


def test_float_missing_bounds_raises():
    with pytest.raises(SearchSpaceError):
        SearchSpace.from_dict({"x": {"type": "float", "low": 0}})


def test_categorical_missing_choices_raises():
    with pytest.raises(SearchSpaceError):
        SearchSpace.from_dict({"x": {"type": "categorical"}})


def test_sample_random_stays_in_bounds():
    space = SearchSpace.from_dict(
        {
            "lr": {"type": "float", "low": 0.1, "high": 1.0, "log": True},
            "n": {"type": "int", "low": 2, "high": 10, "step": 2},
            "kind": {"type": "categorical", "choices": ["a", "b", "c"]},
        }
    )
    rng = np.random.default_rng(0)
    for _ in range(50):
        params = space.sample_random(rng)
        assert 0.1 <= params["lr"] <= 1.0
        assert params["n"] in (2, 4, 6, 8, 10)
        assert params["kind"] in ("a", "b", "c")


def test_suggest_optuna_populates_all_params():
    space = SearchSpace.from_dict(
        {
            "x": {"type": "float", "low": -1.0, "high": 1.0},
            "y": {"type": "int", "low": 0, "high": 5},
            "z": {"type": "categorical", "choices": [1, 2, 3]},
        }
    )
    study = optuna.create_study()

    def objective(trial):
        params = space.suggest_optuna(trial)
        assert set(params) == {"x", "y", "z"}
        return 0.0

    study.optimize(objective, n_trials=3)


def test_grid_enumerates_full_cartesian_product():
    space = SearchSpace.from_dict(
        {
            "n": {"type": "int", "low": 0, "high": 4, "step": 2},
            "kind": {"type": "categorical", "choices": ["a", "b"]},
        }
    )
    combos = space.grid()
    assert len(combos) == 3 * 2
    assert {"n": 0, "kind": "a"} in combos
    assert {"n": 4, "kind": "b"} in combos


def test_grid_rejects_unbounded_float():
    space = SearchSpace.from_dict({"x": {"type": "float", "low": 0.0, "high": 1.0}})
    with pytest.raises(SearchSpaceError):
        space.grid()


def test_snap_skopt_point_rounds_int_to_step_grid():
    space = SearchSpace.from_dict(
        {
            "batch_size": {"type": "int", "low": 16, "high": 256, "step": 16},
            "lr": {"type": "float", "low": 0.0, "high": 1.0},
            "kind": {"type": "categorical", "choices": ["a", "b"]},
        }
    )
    params = space.snap_skopt_point([50, 0.5, "a"])
    assert params["batch_size"] in range(16, 257, 16)
    assert params["batch_size"] == 48
    assert params["lr"] == 0.5
    assert params["kind"] == "a"


def test_snap_skopt_point_clips_to_bounds():
    space = SearchSpace.from_dict({"n": {"type": "int", "low": 0, "high": 10, "step": 3}})
    assert space.snap_skopt_point([10])["n"] == 9  # nearest grid point <= high (0,3,6,9)
    assert space.snap_skopt_point([-5])["n"] == 0


def test_to_optuna_distributions_round_trip():
    space = SearchSpace.from_dict(
        {
            "x": {"type": "float", "low": 0.0, "high": 1.0},
            "n": {"type": "int", "low": 1, "high": 3},
            "kind": {"type": "categorical", "choices": ["a", "b"]},
        }
    )
    distributions = space.to_optuna_distributions()
    assert set(distributions) == {"x", "n", "kind"}
    assert isinstance(distributions["x"], optuna.distributions.FloatDistribution)
    assert isinstance(distributions["n"], optuna.distributions.IntDistribution)
    assert isinstance(distributions["kind"], optuna.distributions.CategoricalDistribution)
