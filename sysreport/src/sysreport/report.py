from __future__ import annotations

from dataclasses import dataclass

from diskcheck.fsutils import human_size

from sysreport.metrics import BatterySnapshot, CpuSnapshot, MemorySnapshot, read_battery, read_cpu, read_memory
from sysreport.storage import DriveUsage, list_drives
from sysreport.thresholds import Thresholds


@dataclass
class SysReport:
    """One point-in-time snapshot of everything `sysreport run` checks."""

    drives: list[DriveUsage]
    cpu: CpuSnapshot
    memory: MemorySnapshot
    battery: BatterySnapshot


def build_report(*, cpu_interval: float = 0.5) -> SysReport:
    """Collect a fresh snapshot. `cpu_interval` blocks that long for an accurate CPU reading."""
    return SysReport(
        drives=list_drives(),
        cpu=read_cpu(interval=cpu_interval),
        memory=read_memory(),
        battery=read_battery(),
    )


def to_dict(report: SysReport, thresholds: Thresholds) -> dict:
    return {
        "drives": [
            {
                "mountpoint": d.mountpoint,
                "free": d.free,
                "free_human": human_size(d.free),
                "total": d.total,
                "free_percent": round(d.free_percent, 1),
                "warn": d.free_percent <= thresholds.storage_min_free_percent,
            }
            for d in report.drives
        ],
        "cpu": {
            "percent": report.cpu.percent,
            "warn": report.cpu.percent >= thresholds.cpu_max_percent,
        },
        "memory": {
            "percent": report.memory.percent,
            "warn": report.memory.percent >= thresholds.memory_max_percent,
        },
        "battery": (
            {
                "percent": report.battery.percent,
                "plugged": report.battery.plugged,
                "warn": (
                    not report.battery.plugged
                    and report.battery.percent is not None
                    and report.battery.percent <= thresholds.battery_min_percent
                ),
            }
            if report.battery.present
            else None
        ),
    }


def format_report(report: SysReport, thresholds: Thresholds, *, highlight_warnings: bool = False) -> str:
    """Render the report as one line of emoji-tagged segments, e.g.

    "💾 C:\\ 空き容量: 45.00 GB (32%) / 🔋 バッテリー: 80% (充電中) / 🖥️ CPU: 12% / 🧠 メモリ: 55%"

    With `highlight_warnings=True`, segments below/above their threshold get a
    trailing "⚠️" mark.
    """

    def mark(is_warn: bool) -> str:
        return " ⚠️" if highlight_warnings and is_warn else ""

    segments: list[str] = []

    for drive in report.drives:
        warn = drive.free_percent <= thresholds.storage_min_free_percent
        segments.append(
            f"💾 {drive.mountpoint} 空き容量: {human_size(drive.free)} ({drive.free_percent:.0f}%){mark(warn)}"
        )

    if report.battery.present:
        state = "充電中" if report.battery.plugged else "バッテリー駆動"
        warn = not report.battery.plugged and (
            report.battery.percent is not None and report.battery.percent <= thresholds.battery_min_percent
        )
        segments.append(f"🔋 バッテリー: {report.battery.percent:.0f}% ({state}){mark(warn)}")

    cpu_warn = report.cpu.percent >= thresholds.cpu_max_percent
    segments.append(f"🖥️ CPU: {report.cpu.percent:.0f}%{mark(cpu_warn)}")

    mem_warn = report.memory.percent >= thresholds.memory_max_percent
    segments.append(f"🧠 メモリ: {report.memory.percent:.0f}%{mark(mem_warn)}")

    return " / ".join(segments)
