from __future__ import annotations

import optuna

from tunelab.config import Config
from tunelab.objective import evaluate
from tunelab.objective.errors import TrialFailed


def run(study: optuna.Study, config: Config) -> None:
    config.budget.require_bound()

    def objective(trial: optuna.Trial) -> float:
        params = config.space.suggest_optuna(trial)
        return evaluate(config.objective, params)

    study.optimize(
        objective,
        n_trials=config.budget.n_trials,
        timeout=config.budget.timeout,
        n_jobs=config.budget.n_jobs,
        catch=(TrialFailed,),
    )
