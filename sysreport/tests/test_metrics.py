from __future__ import annotations

from sysreport.metrics import read_battery, read_cpu, read_memory


def test_read_cpu_returns_percent(fake_hardware):
    snapshot = read_cpu(interval=0)
    assert snapshot.percent == 12.0


def test_read_memory_returns_percent_and_totals(fake_hardware):
    snapshot = read_memory()
    assert snapshot.percent == 55.0
    assert snapshot.total == 16_000_000_000
    assert snapshot.available == 7_200_000_000


def test_read_battery_present(fake_hardware):
    battery = read_battery()
    assert battery.present is True
    assert battery.percent == 80.0
    assert battery.plugged is True


def test_read_battery_absent_on_desktop(monkeypatch):
    monkeypatch.setattr("psutil.sensors_battery", lambda: None)
    battery = read_battery()
    assert battery.present is False
    assert battery.percent is None
