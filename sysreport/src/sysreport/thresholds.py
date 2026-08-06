from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional

from confload import load_config

DEFAULT_STORAGE_MIN_FREE_PERCENT = 10.0
DEFAULT_BATTERY_MIN_PERCENT = 20.0
DEFAULT_CPU_MAX_PERCENT = 90.0
DEFAULT_MEMORY_MAX_PERCENT = 90.0


@dataclass
class Thresholds:
    """Warning thresholds for each metric in the report.

    Storage/battery warn when the value drops *below* their threshold;
    CPU/memory warn when usage rises *above* theirs.
    """

    storage_min_free_percent: float = DEFAULT_STORAGE_MIN_FREE_PERCENT
    battery_min_percent: float = DEFAULT_BATTERY_MIN_PERCENT
    cpu_max_percent: float = DEFAULT_CPU_MAX_PERCENT
    memory_max_percent: float = DEFAULT_MEMORY_MAX_PERCENT


def load_thresholds(config_path: Optional[Path] = None) -> Thresholds:
    """Return `Thresholds`, optionally overridden by a YAML/JSON config file.

    The file may set any subset of the fields on `Thresholds`; unset fields
    keep their default.
    """
    thresholds = Thresholds()
    if config_path is None:
        return thresholds

    config = load_config(config_path)
    overrides = {
        field: config[field]
        for field in (
            "storage_min_free_percent",
            "battery_min_percent",
            "cpu_max_percent",
            "memory_max_percent",
        )
        if field in config
    }
    return replace(thresholds, **overrides)
