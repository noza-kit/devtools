from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from tunelab.space import SearchSpace, SearchSpaceError

VALID_BACKENDS = {"optuna", "skopt", "random", "grid"}
VALID_DIRECTIONS = {"maximize", "minimize"}
VALID_OBJECTIVE_MODES = {"command", "callable"}


class ConfigError(Exception):
    pass


@dataclass
class Budget:
    n_trials: Optional[int] = None
    timeout: Optional[float] = None
    n_jobs: int = 1

    def __post_init__(self) -> None:
        if self.n_jobs < 1:
            raise ConfigError("budget.n_jobs must be >= 1")

    def require_bound(self) -> None:
        """Backends that can run forever (optuna/random) need at least one stop condition."""
        if self.n_trials is None and self.timeout is None:
            raise ConfigError("budget requires at least one of n_trials or timeout")


@dataclass
class ObjectiveSpec:
    mode: str
    command: Optional[str] = None
    result_file: Optional[str] = None
    result_regex: Optional[str] = None
    entrypoint: Optional[str] = None
    timeout_per_trial: Optional[float] = None
    working_dir: Path = field(default_factory=lambda: Path("."))
    env: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.mode not in VALID_OBJECTIVE_MODES:
            raise ConfigError(
                f"objective.mode must be one of {sorted(VALID_OBJECTIVE_MODES)}, got {self.mode!r}"
            )
        if self.mode == "command":
            if not self.command:
                raise ConfigError("objective.mode=command requires 'command'")
            if not self.result_file and not self.result_regex:
                raise ConfigError(
                    "objective.mode=command requires 'result_file' or 'result_regex'"
                )
        if self.mode == "callable" and not self.entrypoint:
            raise ConfigError("objective.mode=callable requires 'entrypoint'")


@dataclass
class Config:
    study: str
    direction: str
    backend: str
    budget: Budget
    space: SearchSpace
    objective: ObjectiveSpec
    path: Optional[Path] = None

    @classmethod
    def from_dict(cls, raw: dict, path: Optional[Path] = None) -> "Config":
        if "study" not in raw:
            raise ConfigError("config missing required key 'study'")
        study = raw["study"]

        direction = raw.get("direction", "minimize")
        if direction not in VALID_DIRECTIONS:
            raise ConfigError(f"direction must be one of {sorted(VALID_DIRECTIONS)}, got {direction!r}")

        backend = raw.get("backend", "optuna")
        if backend not in VALID_BACKENDS:
            raise ConfigError(f"backend must be one of {sorted(VALID_BACKENDS)}, got {backend!r}")

        budget_raw = raw.get("budget") or {}
        budget = Budget(
            n_trials=budget_raw.get("n_trials"),
            timeout=budget_raw.get("timeout"),
            n_jobs=budget_raw.get("n_jobs", 1),
        )

        space_raw = raw.get("space")
        if not space_raw:
            raise ConfigError("config missing required key 'space'")
        try:
            space = SearchSpace.from_dict(space_raw)
        except SearchSpaceError as exc:
            raise ConfigError(str(exc)) from exc

        objective_raw = raw.get("objective")
        if not objective_raw:
            raise ConfigError("config missing required key 'objective'")
        objective_raw = dict(objective_raw)
        working_dir = Path(objective_raw.pop("working_dir", "."))
        objective = ObjectiveSpec(
            mode=objective_raw.get("mode", "command"),
            command=objective_raw.get("command"),
            result_file=objective_raw.get("result_file"),
            result_regex=objective_raw.get("result_regex"),
            entrypoint=objective_raw.get("entrypoint"),
            timeout_per_trial=objective_raw.get("timeout_per_trial"),
            working_dir=working_dir,
            env=objective_raw.get("env") or {},
        )

        return cls(
            study=study,
            direction=direction,
            backend=backend,
            budget=budget,
            space=space,
            objective=objective,
            path=path,
        )

    @classmethod
    def load(cls, path: Path) -> "Config":
        path = Path(path)
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except FileNotFoundError as exc:
            raise ConfigError(f"config file not found: {path}") from exc
        if not isinstance(raw, dict):
            raise ConfigError(f"config file {path} must contain a YAML mapping")
        return cls.from_dict(raw, path=path)
