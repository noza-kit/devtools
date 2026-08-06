from __future__ import annotations

from dataclasses import dataclass

import psutil
from diskcheck.fsutils import human_size


@dataclass
class DriveUsage:
    """Free/used space for one mounted drive."""

    mountpoint: str
    total: int
    used: int
    free: int

    @property
    def free_percent(self) -> float:
        if self.total == 0:
            return 0.0
        return self.free / self.total * 100


def list_drives() -> list[DriveUsage]:
    """Return free/used space for every real, currently-accessible drive.

    Skips CD-ROM/removable-with-no-media entries (empty `fstype`, the marker
    `psutil.disk_partitions` uses for drives it couldn't actually read).
    """
    drives: list[DriveUsage] = []
    for part in psutil.disk_partitions(all=False):
        if not part.fstype:
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except OSError:
            continue
        drives.append(
            DriveUsage(
                mountpoint=part.mountpoint,
                total=usage.total,
                used=usage.used,
                free=usage.free,
            )
        )
    return drives


def format_drive(drive: DriveUsage) -> str:
    return f"{drive.mountpoint} {human_size(drive.free)} 空き ({drive.free_percent:.0f}%)"
