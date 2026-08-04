from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from devtoolbox.orgdir.config import OrgdirConfig


@dataclass
class PlannedMove:
    source: Path
    destination: Path
    category: str


@dataclass
class OrganizeResult:
    moved: list[PlannedMove] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _category_for(name: str, config: OrgdirConfig) -> str:
    ext = Path(name).suffix.lower().lstrip(".")
    if not ext:
        return config.no_extension_category
    for category, extensions in config.categories.items():
        if ext in extensions:
            return category
    return config.default_category


def _resolve_conflict(destination: Path, reserved: set[Path]) -> Path:
    """Find a free path for `destination`, renaming as `name (1).ext`, `name (2).ext`, ... on conflict."""
    if not destination.exists() and destination not in reserved:
        return destination
    stem, suffix, parent = destination.stem, destination.suffix, destination.parent
    counter = 1
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists() and candidate not in reserved:
            return candidate
        counter += 1


def plan_moves(target: Path, config: OrgdirConfig) -> list[PlannedMove]:
    """Compute where each top-level file in `target` would move to, without touching the filesystem."""
    planned: list[PlannedMove] = []
    reserved: set[Path] = set()
    for entry in sorted(target.iterdir()):
        if not entry.is_file() or entry.name in config.ignore:
            continue
        category = _category_for(entry.name, config)
        destination = _resolve_conflict(target / category / entry.name, reserved)
        reserved.add(destination)
        planned.append(PlannedMove(source=entry, destination=destination, category=category))
    return planned


def organize(target: Path, config: OrgdirConfig, dry_run: bool = False) -> OrganizeResult:
    result = OrganizeResult()
    for move in plan_moves(target, config):
        if dry_run:
            result.moved.append(move)
            continue
        try:
            move.destination.parent.mkdir(parents=True, exist_ok=True)
            move.source.rename(move.destination)
            result.moved.append(move)
        except OSError as exc:
            result.errors.append(f"{move.source}: {exc}")
    return result


def append_log(log_path: Path, target: Path, moved: list[PlannedMove]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with log_path.open("a", encoding="utf-8") as f:
        for move in moved:
            f.write(f"{timestamp}\t{target}\t{move.source.name} -> {move.category}/{move.destination.name}\n")
