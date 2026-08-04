from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

logger = logging.getLogger(__name__)

# A step receives the decoded frame plus a shared context dict (earlier
# steps' results, for steps that want to build on each other) and returns a
# dict of result values to report for that step.
StepFunc = Callable[[np.ndarray, dict], dict]


@dataclass
class Pipeline:
    """An ordered list of swappable frame-processing functions.

    Each step is called as `func(frame, context)` and must return a dict.
    A step's return value is merged into `context` under its name, so later
    steps can reuse earlier results (e.g. a shared grayscale conversion).
    """

    steps: list[tuple[str, StepFunc]] = field(default_factory=list)

    def add_step(self, func: StepFunc, name: str | None = None) -> "Pipeline":
        self.steps.append((name or func.__name__, func))
        return self

    def process(self, frame: np.ndarray) -> dict:
        context: dict = {}
        results: dict = {}
        for name, func in self.steps:
            try:
                step_result = func(frame, context)
            except Exception as exc:  # a bad step shouldn't take down the others
                logger.exception("Pipeline step %r failed", name)
                results[name] = {"error": str(exc)}
                continue
            results[name] = step_result
            context[name] = step_result
        return results
