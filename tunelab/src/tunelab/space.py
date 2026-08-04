from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any, Union

import numpy as np
import optuna


class SearchSpaceError(Exception):
    pass


@dataclass(frozen=True)
class FloatParam:
    name: str
    low: float
    high: float
    log: bool = False

    def suggest_optuna(self, trial: optuna.Trial) -> float:
        return trial.suggest_float(self.name, self.low, self.high, log=self.log)

    def sample_random(self, rng: np.random.Generator) -> float:
        if self.log:
            low, high = np.log(self.low), np.log(self.high)
            return float(np.exp(rng.uniform(low, high)))
        return float(rng.uniform(self.low, self.high))

    def to_optuna_distribution(self) -> optuna.distributions.BaseDistribution:
        return optuna.distributions.FloatDistribution(self.low, self.high, log=self.log)

    def to_skopt_dimension(self):
        from skopt.space import Real

        return Real(self.low, self.high, prior="log-uniform" if self.log else "uniform", name=self.name)


@dataclass(frozen=True)
class IntParam:
    name: str
    low: int
    high: int
    step: int = 1

    def suggest_optuna(self, trial: optuna.Trial) -> int:
        return trial.suggest_int(self.name, self.low, self.high, step=self.step)

    def sample_random(self, rng: np.random.Generator) -> int:
        n_steps = (self.high - self.low) // self.step
        return int(self.low + int(rng.integers(0, n_steps + 1)) * self.step)

    def grid_values(self) -> list[int]:
        return list(range(self.low, self.high + 1, self.step))

    def to_optuna_distribution(self) -> optuna.distributions.BaseDistribution:
        return optuna.distributions.IntDistribution(self.low, self.high, step=self.step)

    def to_skopt_dimension(self):
        from skopt.space import Integer

        return Integer(self.low, self.high, name=self.name)


@dataclass(frozen=True)
class CategoricalParam:
    name: str
    choices: tuple

    def suggest_optuna(self, trial: optuna.Trial) -> Any:
        return trial.suggest_categorical(self.name, list(self.choices))

    def sample_random(self, rng: np.random.Generator) -> Any:
        idx = int(rng.integers(0, len(self.choices)))
        return self.choices[idx]

    def grid_values(self) -> list[Any]:
        return list(self.choices)

    def to_optuna_distribution(self) -> optuna.distributions.BaseDistribution:
        return optuna.distributions.CategoricalDistribution(list(self.choices))

    def to_skopt_dimension(self):
        from skopt.space import Categorical

        return Categorical(list(self.choices), name=self.name)


Param = Union[FloatParam, IntParam, CategoricalParam]


@dataclass
class SearchSpace:
    params: list

    @classmethod
    def from_dict(cls, raw: dict[str, dict]) -> "SearchSpace":
        params: list[Param] = []
        for name, spec in raw.items():
            spec = dict(spec)
            ptype = spec.pop("type", None)
            if ptype == "float":
                if "low" not in spec or "high" not in spec:
                    raise SearchSpaceError(f"Parameter {name!r}: float requires 'low' and 'high'")
                params.append(
                    FloatParam(
                        name=name,
                        low=float(spec["low"]),
                        high=float(spec["high"]),
                        log=bool(spec.get("log", False)),
                    )
                )
            elif ptype == "int":
                if "low" not in spec or "high" not in spec:
                    raise SearchSpaceError(f"Parameter {name!r}: int requires 'low' and 'high'")
                params.append(
                    IntParam(
                        name=name,
                        low=int(spec["low"]),
                        high=int(spec["high"]),
                        step=int(spec.get("step", 1)),
                    )
                )
            elif ptype == "categorical":
                choices = spec.get("choices")
                if not choices:
                    raise SearchSpaceError(f"Parameter {name!r}: categorical requires 'choices'")
                params.append(CategoricalParam(name=name, choices=tuple(choices)))
            else:
                raise SearchSpaceError(
                    f"Parameter {name!r}: unknown type {ptype!r} (expected float/int/categorical)"
                )
        if not params:
            raise SearchSpaceError("Search space is empty")
        return cls(params=params)

    @property
    def names(self) -> list[str]:
        return [p.name for p in self.params]

    def suggest_optuna(self, trial: optuna.Trial) -> dict[str, Any]:
        return {p.name: p.suggest_optuna(trial) for p in self.params}

    def sample_random(self, rng: np.random.Generator) -> dict[str, Any]:
        return {p.name: p.sample_random(rng) for p in self.params}

    def to_optuna_distributions(self) -> dict[str, optuna.distributions.BaseDistribution]:
        return {p.name: p.to_optuna_distribution() for p in self.params}

    def to_skopt_dimensions(self) -> list:
        return [p.to_skopt_dimension() for p in self.params]

    def snap_skopt_point(self, x: list) -> dict[str, Any]:
        """Map a raw skopt-sampled point back to params valid for this space.

        skopt.space.Integer has no notion of a step, so it can return any
        integer in [low, high]; round it to the nearest value on this
        param's step grid so it matches the corresponding optuna
        IntDistribution(step=...) used to record the trial.
        """
        params: dict[str, Any] = {}
        for p, raw in zip(self.params, x):
            if isinstance(p, IntParam) and p.step != 1:
                n_steps = round((raw - p.low) / p.step)
                max_steps = (p.high - p.low) // p.step
                n_steps = max(0, min(n_steps, max_steps))
                params[p.name] = p.low + n_steps * p.step
            else:
                params[p.name] = raw
        return params

    def grid(self) -> list[dict[str, Any]]:
        names = []
        value_lists = []
        for p in self.params:
            if not hasattr(p, "grid_values"):
                raise SearchSpaceError(
                    f"Parameter {p.name!r} is a float without a fixed step and can't be used "
                    "for grid search; use backend: random or add a discrete 'step'/'choices'"
                )
            names.append(p.name)
            value_lists.append(p.grid_values())
        return [dict(zip(names, combo)) for combo in itertools.product(*value_lists)]
