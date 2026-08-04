from __future__ import annotations

from typing import Callable

import optuna

from tunelab.backends import optuna_backend, random_backend
from tunelab.config import Config


class BackendError(Exception):
    pass


def _run_skopt(study: optuna.Study, config: Config) -> None:
    try:
        from tunelab.backends import skopt_backend
    except ImportError as exc:
        raise BackendError(
            "backend 'skopt' requires scikit-optimize. Install with: pip install tunelab[skopt]"
        ) from exc
    skopt_backend.run(study, config)


_BACKENDS: dict[str, Callable[[optuna.Study, Config], None]] = {
    "optuna": optuna_backend.run,
    "random": random_backend.run_random,
    "grid": random_backend.run_grid,
    "skopt": _run_skopt,
}


def get_backend(name: str) -> Callable[[optuna.Study, Config], None]:
    try:
        return _BACKENDS[name]
    except KeyError as exc:
        raise BackendError(f"Unknown backend {name!r}") from exc
