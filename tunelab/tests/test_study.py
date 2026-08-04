from __future__ import annotations

import optuna
import pytest

from tunelab.config import Budget, Config, ObjectiveSpec
from tunelab.paths import study_db_path
from tunelab.space import SearchSpace
from tunelab.study import StudyNotFoundError, delete_study, load_study, open_study


def _config(name="demo") -> Config:
    space = SearchSpace.from_dict({"x": {"type": "float", "low": 0.0, "high": 1.0}})
    objective = ObjectiveSpec(mode="callable", entrypoint="unused:unused")
    return Config(
        study=name, direction="minimize", backend="optuna",
        budget=Budget(n_trials=1), space=space, objective=objective,
    )


def _add_dummy_trial(study: optuna.Study, config: Config) -> None:
    trial = optuna.trial.create_trial(
        state=optuna.trial.TrialState.COMPLETE,
        value=1.0,
        params={"x": 0.5},
        distributions=config.space.to_optuna_distributions(),
    )
    study.add_trial(trial)


def test_open_study_persists_and_resumes(tunelab_home):
    config = _config()
    study = open_study(config)
    _add_dummy_trial(study, config)

    resumed = open_study(config)
    assert len(resumed.trials) == 1


def test_open_study_fresh_discards_previous_trials(tunelab_home):
    config = _config()
    study = open_study(config)
    _add_dummy_trial(study, config)

    fresh_study = open_study(config, fresh=True)
    assert len(fresh_study.trials) == 0


def test_load_study_missing_raises(tunelab_home):
    with pytest.raises(StudyNotFoundError):
        load_study("does-not-exist")


def test_load_study_returns_existing(tunelab_home):
    config = _config()
    open_study(config)
    loaded = load_study("demo")
    assert loaded.study_name == "demo"


def test_delete_study_removes_db_file(tunelab_home):
    config = _config()
    open_study(config)
    assert study_db_path("demo").exists()

    delete_study("demo")
    assert not study_db_path("demo").exists()
    with pytest.raises(StudyNotFoundError):
        load_study("demo")


def test_delete_missing_study_raises(tunelab_home):
    with pytest.raises(StudyNotFoundError):
        delete_study("nope")
