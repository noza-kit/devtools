from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import psutil


@dataclass
class CpuSnapshot:
    """Point-in-time CPU utilization."""

    percent: float


@dataclass
class MemorySnapshot:
    """Point-in-time RAM utilization."""

    percent: float
    total: int
    available: int


@dataclass
class BatterySnapshot:
    """Battery state, or `present=False` on desktops with no battery sensor."""

    present: bool
    percent: Optional[float] = None
    plugged: Optional[bool] = None


def read_cpu(*, interval: float = 0.5) -> CpuSnapshot:
    """Sample CPU usage over `interval` seconds (blocking, for an accurate reading)."""
    return CpuSnapshot(percent=psutil.cpu_percent(interval=interval))


def read_memory() -> MemorySnapshot:
    vm = psutil.virtual_memory()
    return MemorySnapshot(percent=vm.percent, total=vm.total, available=vm.available)


def read_battery() -> BatterySnapshot:
    battery = psutil.sensors_battery()
    if battery is None:
        return BatterySnapshot(present=False)
    return BatterySnapshot(present=True, percent=battery.percent, plugged=battery.power_plugged)
