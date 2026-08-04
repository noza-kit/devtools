from __future__ import annotations

import itertools
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Iterable, Iterator

import numpy as np
import optuna

from tunelab.config import Config
from tunelab.objective import evaluate
from tunelab.objective.errors import TrialFailed


def _safe_evaluate(objective_spec, params: dict[str, Any]) -> tuple[float | None, bool]:
    try:
        return evaluate(objective_spec, params), False
    except TrialFailed:
        return None, True


def _record_trial(
    study: optuna.Study,
    distributions: dict[str, optuna.distributions.BaseDistribution],
    params: dict[str, Any],
    value: float | None,
    failed: bool,
) -> None:
    if failed:
        trial = optuna.trial.create_trial(
            params=params, distributions=distributions, state=optuna.trial.TrialState.FAIL
        )
    else:
        trial = optuna.trial.create_trial(
            params=params,
            distributions=distributions,
            value=value,
            state=optuna.trial.TrialState.COMPLETE,
        )
    study.add_trial(trial)


def _run_trials(study: optuna.Study, config: Config, params_iter: Iterable[dict[str, Any]]) -> None:
    """Consume `params_iter` in batches of budget.n_jobs until budget.n_trials/timeout is hit."""
    distributions = config.space.to_optuna_distributions()
    budget = config.budget
    start = time.monotonic()
    completed = 0
    it: Iterator[dict[str, Any]] = iter(params_iter)

    while True:
        if budget.n_trials is not None and completed >= budget.n_trials:
            return
        if budget.timeout is not None and (time.monotonic() - start) >= budget.timeout:
            return

        batch_size = budget.n_jobs
        if budget.n_trials is not None:
            batch_size = min(batch_size, budget.n_trials - completed)

        batch = list(itertools.islice(it, batch_size))
        if not batch:
            return

        if budget.n_jobs > 1:
            with ThreadPoolExecutor(max_workers=budget.n_jobs) as pool:
                results = list(pool.map(lambda p: _safe_evaluate(config.objective, p), batch))
        else:
            results = [_safe_evaluate(config.objective, p) for p in batch]

        for params, (value, failed) in zip(batch, results):
            _record_trial(study, distributions, params, value, failed)
            completed += 1


def run_random(study: optuna.Study, config: Config) -> None:
    config.budget.require_bound()
    rng = np.random.default_rng()
    params_iter = (config.space.sample_random(rng) for _ in itertools.count())
    _run_trials(study, config, params_iter)


def run_grid(study: optuna.Study, config: Config) -> None:
    _run_trials(study, config, config.space.grid())
