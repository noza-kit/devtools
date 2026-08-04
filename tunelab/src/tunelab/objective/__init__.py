from __future__ import annotations

from typing import Any

from tunelab.config import ObjectiveSpec
from tunelab.objective.command import run_command_objective
from tunelab.objective.errors import ObjectiveError, TrialFailed
from tunelab.objective.pyfunc import run_pyfunc_objective

__all__ = ["evaluate", "ObjectiveError", "TrialFailed"]


def evaluate(spec: ObjectiveSpec, params: dict[str, Any]) -> float:
    if spec.mode == "command":
        return run_command_objective(spec, params)
    return run_pyfunc_objective(spec, params)
