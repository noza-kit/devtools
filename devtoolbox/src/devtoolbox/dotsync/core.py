from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class LinkResult:
    linked: list[str] = field(default_factory=list)
    already_linked: list[str] = field(default_factory=list)
    backed_up: list[str] = field(default_factory=list)
    skipped_conflicts: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class UnlinkResult:
    removed: list[str] = field(default_factory=list)
    restored: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _dotfile_entries(source_dir: Path) -> list[Path]:
    """Only top-level entries starting with '.' are treated as dotfiles.

    This keeps repo housekeeping files (README.md, install.sh, ...) out of
    $HOME without needing a separate ignore list.
    """
    return sorted(p for p in source_dir.iterdir() if p.name.startswith("."))


def _target_for(home: Path, entry: Path) -> Path:
    return home / entry.name


def _is_linked_to(target: Path, entry: Path) -> bool:
    return target.is_symlink() and target.resolve() == entry.resolve()


def link_all(source_dir: Path, home: Path, force: bool = False) -> LinkResult:
    result = LinkResult()
    for entry in _dotfile_entries(source_dir):
        target = _target_for(home, entry)

        if _is_linked_to(target, entry):
            result.already_linked.append(str(target))
            continue

        if target.exists() or target.is_symlink():
            if not force:
                result.skipped_conflicts.append(str(target))
                continue
            backup = target.with_name(target.name + ".bak")
            if backup.exists():
                result.errors.append(
                    f"{target}: backup {backup} already exists, skipping"
                )
                continue
            target.rename(backup)
            result.backed_up.append(str(backup))

        try:
            target.symlink_to(entry, target_is_directory=entry.is_dir())
            result.linked.append(str(target))
        except OSError as exc:
            result.errors.append(f"{target}: {exc}")

    return result


def unlink_all(source_dir: Path, home: Path) -> UnlinkResult:
    result = UnlinkResult()
    for entry in _dotfile_entries(source_dir):
        target = _target_for(home, entry)

        if not target.is_symlink():
            continue

        if not _is_linked_to(target, entry):
            result.errors.append(f"{target}: symlink points elsewhere, skipping")
            continue

        target.unlink()
        result.removed.append(str(target))

        backup = target.with_name(target.name + ".bak")
        if backup.exists():
            backup.rename(target)
            result.restored.append(str(target))

    return result


def status_all(source_dir: Path, home: Path) -> list[tuple[str, str]]:
    statuses: list[tuple[str, str]] = []
    for entry in _dotfile_entries(source_dir):
        target = _target_for(home, entry)
        if _is_linked_to(target, entry):
            statuses.append((entry.name, "linked"))
        elif target.exists() or target.is_symlink():
            statuses.append((entry.name, "conflict"))
        else:
            statuses.append((entry.name, "missing"))
    return statuses
