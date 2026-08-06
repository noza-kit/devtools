from __future__ import annotations

from sysreport.report import build_report, format_report, to_dict
from sysreport.thresholds import Thresholds


def test_build_report_aggregates_all_metrics(fake_disk, fake_hardware):
    report = build_report(cpu_interval=0)

    assert len(report.drives) == 1
    assert report.cpu.percent == 12.0
    assert report.memory.percent == 55.0
    assert report.battery.percent == 80.0


def test_format_report_contains_all_emoji_sections(fake_disk, fake_hardware):
    report = build_report(cpu_interval=0)
    text = format_report(report, Thresholds())

    assert "💾" in text
    assert "🔋" in text
    assert "🖥️" in text
    assert "🧠" in text


def test_format_report_no_warning_marks_by_default(fake_disk, fake_hardware):
    report = build_report(cpu_interval=0)
    thresholds = Thresholds(storage_min_free_percent=50)  # 20% free < 50% threshold -> would warn

    text = format_report(report, thresholds, highlight_warnings=False)

    assert "⚠️" not in text


def test_format_report_highlights_below_threshold_storage(fake_disk, fake_hardware):
    report = build_report(cpu_interval=0)
    thresholds = Thresholds(storage_min_free_percent=50)  # drive is at 20% free

    text = format_report(report, thresholds, highlight_warnings=True)

    assert "⚠️" in text


def test_format_report_does_not_highlight_when_above_threshold(fake_disk, fake_hardware):
    report = build_report(cpu_interval=0)
    thresholds = Thresholds()  # default 10% min, drive is at 20% free -> fine

    text = format_report(report, thresholds, highlight_warnings=True)

    assert "⚠️" not in text


def test_format_report_skips_battery_section_when_absent(fake_disk, monkeypatch):
    monkeypatch.setattr("psutil.cpu_percent", lambda interval=None: 12.0)
    from collections import namedtuple

    VMem = namedtuple("VMem", ["total", "available", "percent", "used", "free"])
    monkeypatch.setattr(
        "psutil.virtual_memory", lambda: VMem(total=1, available=1, percent=10.0, used=0, free=1)
    )
    monkeypatch.setattr("psutil.sensors_battery", lambda: None)

    report = build_report(cpu_interval=0)
    text = format_report(report, Thresholds())

    assert "🔋" not in text


def test_to_dict_flags_warnings(fake_disk, fake_hardware):
    report = build_report(cpu_interval=0)
    thresholds = Thresholds(storage_min_free_percent=50, cpu_max_percent=5, memory_max_percent=5, battery_min_percent=95)

    data = to_dict(report, thresholds)

    assert data["drives"][0]["warn"] is True
    assert data["cpu"]["warn"] is True
    assert data["memory"]["warn"] is True
    # battery is plugged in, so it never warns regardless of percent
    assert data["battery"]["warn"] is False
