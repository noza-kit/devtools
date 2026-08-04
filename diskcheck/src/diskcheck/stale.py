from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Optional

from diskcheck.fsutils import human_size

SECONDS_PER_DAY = 86400


@dataclass
class StaleFile:
    path: Path
    size: int
    last_accessed: float

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "size": self.size,
            "size_human": human_size(self.size),
            "last_accessed": datetime.fromtimestamp(self.last_accessed).isoformat(timespec="seconds"),
        }


def find_stale_files(
    root: Path,
    *,
    extensions: Iterable[str],
    older_than_days: int = 180,
    now: Optional[float] = None,
    on_progress: Optional[Callable[[], None]] = None,
) -> list[StaleFile]:
    """Find files under `root` whose extension is in `extensions` and whose
    last-access time is older than `older_than_days`, sorted by size descending."""
    root = Path(root)
    ext_set = {e.lower() for e in extensions}
    cutoff = (now if now is not None else time.time()) - older_than_days * SECONDS_PER_DAY

    results: list[StaleFile] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if on_progress:
            on_progress()
        if path.suffix.lower() not in ext_set:
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        if stat.st_atime > cutoff:
            continue
        results.append(StaleFile(path=path, size=stat.st_size, last_accessed=stat.st_atime))

    results.sort(key=lambda f: f.size, reverse=True)
    return results
