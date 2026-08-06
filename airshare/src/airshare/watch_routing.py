from __future__ import annotations

from pathlib import Path

from airshare.files import _avoid_collision
from airshare.watch_config import RoutingRule


def pick_destination(path: Path, routing: tuple[RoutingRule, ...], fallback: Path) -> Path:
    """The first rule whose `extensions` contains `path`'s suffix wins;
    a file matching no rule stays in `fallback` (the inbox itself)."""
    ext = path.suffix.lower()
    for rule in routing:
        if ext in rule.extensions:
            return rule.destination
    return fallback


def route_file(path: Path, routing: tuple[RoutingRule, ...], fallback: Path) -> Path:
    """Moves `path` into its resolved destination folder (created if
    needed), renaming on collision rather than overwriting. A file
    already in its resolved destination (fallback == path.parent) is
    left in place rather than "moved" onto itself."""
    destination_dir = pick_destination(path, routing, fallback)
    if destination_dir == path.parent:
        return path

    destination_dir.mkdir(parents=True, exist_ok=True)
    target = _avoid_collision(destination_dir / path.name)
    path.rename(target)
    return target
