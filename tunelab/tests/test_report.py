from __future__ import annotations

import optuna
import pytest

from tunelab import report

DIST = {"x": optuna.distributions.FloatDistribution(0.0, 10.0)}


def _study_with_trials() -> optuna.Study:
    study = optuna.create_study(direction="minimize")
    for x, value in [(1.0, 4.0), (3.0, 0.0), (7.0, 16.0)]:
        study.add_trial(
            optuna.trial.create_trial(
                state=optuna.trial.TrialState.COMPLETE, value=value, params={"x": x}, distributions=DIST
            )
        )
    study.add_trial(
        optuna.trial.create_trial(state=optuna.trial.TrialState.FAIL, params={"x": 9.0}, distributions=DIST)
    )
    return study


def test_summarize_reports_counts_and_best():
    study = _study_with_trials()
    summary = report.summarize(study)
    assert summary["n_trials"] == 4
    assert summary["states"] == {"COMPLETE": 3, "FAIL": 1}
    assert summary["best"]["value"] == 0.0
    assert summary["best"]["params"] == {"x": 3.0}


def test_summarize_with_no_completed_trials():
    study = optuna.create_study(direction="minimize")
    study.add_trial(
        optuna.trial.create_trial(state=optuna.trial.TrialState.FAIL, params={"x": 1.0}, distributions=DIST)
    )
    summary = report.summarize(study)
    assert summary["best"] is None


def test_top_trials_orders_by_value_for_minimize():
    study = _study_with_trials()
    top = report.top_trials(study, n=2)
    assert [t.value for t in top] == [0.0, 4.0]


def test_top_trials_orders_by_value_for_maximize():
    study = optuna.create_study(direction="maximize")
    for x, value in [(1.0, 4.0), (3.0, 9.0), (7.0, 1.0)]:
        study.add_trial(
            optuna.trial.create_trial(
                state=optuna.trial.TrialState.COMPLETE, value=value, params={"x": x}, distributions=DIST
            )
        )
    top = report.top_trials(study, n=1)
    assert top[0].value == 9.0


def test_list_trials_filters_by_state():
    study = _study_with_trials()
    failed = report.list_trials(study, state="fail")
    assert len(failed) == 1
    assert failed[0].state == optuna.trial.TrialState.FAIL


def test_list_trials_unknown_state_raises():
    study = _study_with_trials()
    with pytest.raises(ValueError):
        report.list_trials(study, state="bogus")


def test_list_trials_sort_by_value():
    study = _study_with_trials()
    trials = report.list_trials(study, sort="value")
    values = [t.value for t in trials if t.value is not None]
    assert values == sorted(values)


def test_export_csv_writes_all_trials(tmp_path):
    study = _study_with_trials()
    output = tmp_path / "results.csv"
    n = report.export_csv(study, output)
    assert n == 4
    content = output.read_text(encoding="utf-8")
    lines = content.strip().splitlines()
    assert lines[0] == "number,state,value,duration_sec,x"
    assert len(lines) == 5
