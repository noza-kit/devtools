from __future__ import annotations

from collections import namedtuple

import pytest

_SDiskPart = namedtuple("_SDiskPart", ["device", "mountpoint", "fstype", "opts"])
_SDiskUsage = namedtuple("_SDiskUsage", ["total", "used", "free", "percent"])
_SVMem = namedtuple("_SVMem", ["total", "available", "percent", "used", "free"])
_SBattery = namedtuple("_SBattery", ["percent", "secsleft", "power_plugged"])


@pytest.fixture
def fake_disk(monkeypatch):
    """Stub `psutil.disk_partitions`/`disk_usage` with one C: drive, 20% free."""
    partitions = [_SDiskPart("C:\\", "C:\\", "NTFS", "rw,fixed")]
    usage = _SDiskUsage(total=100_000_000_000, used=80_000_000_000, free=20_000_000_000, percent=80.0)

    monkeypatch.setattr("psutil.disk_partitions", lambda all=False: partitions)
    monkeypatch.setattr("psutil.disk_usage", lambda mountpoint: usage)
    return usage


@pytest.fixture
def fake_hardware(monkeypatch):
    """Stub `psutil.cpu_percent`/`virtual_memory`/`sensors_battery` with fixed values."""
    monkeypatch.setattr("psutil.cpu_percent", lambda interval=None: 12.0)
    monkeypatch.setattr(
        "psutil.virtual_memory",
        lambda: _SVMem(total=16_000_000_000, available=7_200_000_000, percent=55.0, used=8_800_000_000, free=7_200_000_000),
    )
    monkeypatch.setattr("psutil.sensors_battery", lambda: _SBattery(percent=80.0, secsleft=None, power_plugged=True))
