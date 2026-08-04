from __future__ import annotations

import importlib
from typing import Any, Callable

from tunelab.config import ObjectiveSpec
from tunelab.objective.errors import ObjectiveError


def load_entrypoint(entrypoint: str) -> Callable[[dict[str, Any]], float]:
    if ":" not in entrypoint:
        raise ObjectiveError(f"entrypoint must be 'module:function', got {entrypoint!r}")
    module_name, func_name = entrypoint.split(":", 1)
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise ObjectiveError(f"could not import module {module_name!r}: {exc}") from exc
    try:
        func = getattr(module, func_name)
    except AttributeError as exc:
        raise ObjectiveError(f"module {module_name!r} has no attribute {func_name!r}") from exc
    if not callable(func):
        raise ObjectiveError(f"{entrypoint} is not callable")
    return func


def run_pyfunc_objective(spec: ObjectiveSpec, params: dict[str, Any]) -> float:
    """Call the configured `module:function` in-process with the trial's params.

    The target function must accept a single dict of {param_name: value} and
    return a float score. Exceptions it raises propagate as-is; wrap the call
    in your own try/except and raise TrialFailed if you want a bad trial
    recorded instead of aborting the whole run.
    """
    func = load_entrypoint(spec.entrypoint)
    return float(func(params))
