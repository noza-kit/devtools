from __future__ import annotations

import time

import optuna
from skopt import Optimizer

from tunelab.config import Config
from tunelab.objective import evaluate
from tunelab.objective.errors import TrialFailed


def run(study: optuna.Study, config: Config) -> None:
    """Bayesian optimization via scikit-optimize's ask/tell loop.

    Runs sequentially (skopt's Optimizer.ask/tell is inherently serial), so
    budget.n_jobs is ignored here unlike the optuna/random backends.
    """
    config.budget.require_bound()

    space = config.space
    dimensions = space.to_skopt_dimensions()
    distributions = space.to_optuna_distributions()
    minimize = config.direction == "minimize"

    optimizer = Optimizer(dimensions=dimensions, base_estimator="GP", acq_func="EI")

    budget = config.budget
    start = time.monotonic()
    completed = 0

    while True:
        if budget.n_trials is not None and completed >= budget.n_trials:
            break
        if budget.timeout is not None and (time.monotonic() - start) >= budget.timeout:
            break

        x = optimizer.ask()
        params = space.snap_skopt_point(x)

        try:
            value = evaluate(config.objective, params)
        except TrialFailed:
            # Tell the optimizer this region is bad so it steers away, and
            # record the trial as failed.
            optimizer.tell(x, float("inf"))
            trial = optuna.trial.create_trial(
                params=params, distributions=distributions, state=optuna.trial.TrialState.FAIL
            )
        else:
            optimizer.tell(x, value if minimize else -value)
            trial = optuna.trial.create_trial(
                params=params,
                distributions=distributions,
                value=value,
                state=optuna.trial.TrialState.COMPLETE,
            )

        study.add_trial(trial)
        completed += 1
