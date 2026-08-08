from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class LargeFile:
    path: Path
    size_bytes: int


def scan_large_files(project: Path, threshold_bytes: int) -> list[LargeFile]:
    """Files under PROJECT whose size is >= threshold_bytes, largest first."""
    found = []
    for f in project.rglob("*"):
        if not f.is_file():
            continue
        size = f.stat().st_size
        if size >= threshold_bytes:
            found.append(LargeFile(path=f, size_bytes=size))
    found.sort(key=lambda lf: lf.size_bytes, reverse=True)
    return found
