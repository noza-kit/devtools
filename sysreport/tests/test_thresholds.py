from __future__ import annotations

import pytest
from confload import ConfigError

from sysreport.thresholds import Thresholds, load_thresholds


def test_load_thresholds_without_config_returns_defaults():
    thresholds = load_thresholds()
    assert thresholds == Thresholds()


def test_load_thresholds_applies_partial_overrides(tmp_path):
    config_path = tmp_path / "thresholds.yaml"
    config_path.write_text("storage_min_free_percent: 5\nbattery_min_percent: 15\n", encoding="utf-8")

    thresholds = load_thresholds(config_path)

    assert thresholds.storage_min_free_percent == 5
    assert thresholds.battery_min_percent == 15
    assert thresholds.cpu_max_percent == Thresholds().cpu_max_percent
    assert thresholds.memory_max_percent == Thresholds().memory_max_percent


def test_load_thresholds_missing_file_raises(tmp_path):
    with pytest.raises(ConfigError):
        load_thresholds(tmp_path / "missing.yaml")
