from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path
from typing import Any, Optional

import optuna

TrialState = optuna.trial.TrialState


def summarize(study: optuna.Study) -> dict[str, Any]:
    trials = study.trials
    states: dict[str, int] = {}
    for t in trials:
        states[t.state.name] = states.get(t.state.name, 0) + 1

    best = None
    completed = [t for t in trials if t.state == TrialState.COMPLETE]
    if completed:
        best_trial = study.best_trial
        best = {"number": best_trial.number, "value": best_trial.value, "params": best_trial.params}

    return {
        "study_name": study.study_name,
        "direction": study.direction.name.lower(),
        "n_trials": len(trials),
        "states": states,
        "best": best,
    }


def top_trials(study: optuna.Study, n: int = 5) -> list[optuna.trial.FrozenTrial]:
    completed = [t for t in study.trials if t.state == TrialState.COMPLETE]
    reverse = study.direction == optuna.study.StudyDirection.MAXIMIZE
    return sorted(completed, key=lambda t: t.value, reverse=reverse)[:n]


def list_trials(
    study: optuna.Study, state: Optional[str] = None, sort: str = "number"
) -> list[optuna.trial.FrozenTrial]:
    trials = study.trials
    if state:
        try:
            target = TrialState[state.upper()]
        except KeyError as exc:
            raise ValueError(f"Unknown state {state!r}") from exc
        trials = [t for t in trials if t.state == target]

    if sort == "value":
        reverse = study.direction == optuna.study.StudyDirection.MAXIMIZE
        with_value = [t for t in trials if t.value is not None]
        without_value = [t for t in trials if t.value is None]
        return sorted(with_value, key=lambda t: t.value, reverse=reverse) + without_value
    if sort == "duration":
        return sorted(trials, key=lambda t: t.duration or dt.timedelta(0), reverse=True)
    return sorted(trials, key=lambda t: t.number)


def export_csv(study: optuna.Study, output: Path) -> int:
    trials = study.trials
    param_names = sorted({name for t in trials for name in t.params})

    with output.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["number", "state", "value", "duration_sec", *param_names])
        for t in trials:
            duration = t.duration.total_seconds() if t.duration else ""
            writer.writerow(
                [
                    t.number,
                    t.state.name,
                    t.value if t.value is not None else "",
                    duration,
                    *(t.params.get(name, "") for name in param_names),
                ]
            )
    return len(trials)


def plot_report(study: optuna.Study, output: Path) -> None:
    try:
        from optuna.visualization import (
            plot_optimization_history,
            plot_parallel_coordinate,
            plot_param_importances,
        )
    except ImportError as exc:
        raise RuntimeError("plotting requires the 'viz' extra: pip install tunelab[viz]") from exc

    figs = [plot_optimization_history(study)]
    completed = [t for t in study.trials if t.state == TrialState.COMPLETE]
    if len(completed) >= 2:
        figs.append(plot_param_importances(study))
        figs.append(plot_parallel_coordinate(study))

    html_parts = [fig.to_html(full_html=False, include_plotlyjs="cdn") for fig in figs]
    output.write_text(
        f"<html><head><title>tunelab: {study.study_name}</title></head>"
        f"<body>{''.join(html_parts)}</body></html>",
        encoding="utf-8",
    )
