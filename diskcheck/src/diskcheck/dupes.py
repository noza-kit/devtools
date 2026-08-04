from __future__ import annotations

import hashlib
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from rich.console import Console

from diskcheck.fsutils import human_size

_HASH_CHUNK_SIZE = 1024 * 1024


@dataclass
class FileInfo:
    path: Path
    mtime: float

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "mtime": datetime.fromtimestamp(self.mtime).isoformat(timespec="seconds"),
        }


@dataclass
class DupGroup:
    digest: str
    size: int
    files: list[FileInfo] = field(default_factory=list)

    @property
    def wasted_bytes(self) -> int:
        """Space that would be reclaimed by keeping only one copy."""
        return self.size * (len(self.files) - 1)

    def to_dict(self) -> dict:
        return {
            "sha256": self.digest,
            "size": self.size,
            "size_human": human_size(self.size),
            "wasted_bytes": self.wasted_bytes,
            "wasted_human": human_size(self.wasted_bytes),
            "files": [f.to_dict() for f in self.files],
        }


def hash_file(path: Path, *, chunk_size: int = _HASH_CHUNK_SIZE) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def find_duplicate_groups(
    root: Path,
    *,
    min_size: int = 1,
    max_workers: Optional[int] = None,
    on_progress: Optional[Callable[[], None]] = None,
) -> list[DupGroup]:
    """Find groups of files under `root` with identical content.

    Two-phase approach for performance: first bucket files by size (cheap,
    via stat), then only compute SHA256 (expensive) for files that share a
    size with at least one other file. Hashing is parallelized with a thread
    pool since it's I/O-bound.
    """
    root = Path(root)
    size_buckets: dict[int, list[tuple[Path, float]]] = defaultdict(list)

    for dirpath, _dirnames, filenames in os.walk(root, followlinks=False):
        for name in filenames:
            file_path = Path(dirpath) / name
            try:
                stat = file_path.stat()
            except OSError:
                continue
            if stat.st_size < min_size:
                continue
            size_buckets[stat.st_size].append((file_path, stat.st_mtime))

    all_candidates = [
        (size, path, mtime) for size, entries in size_buckets.items() if len(entries) > 1 for path, mtime in entries
    ]

    def hash_one(item: tuple[int, Path, float]) -> tuple[int, Path, float, Optional[str]]:
        size, path, mtime = item
        try:
            digest = hash_file(path)
        except OSError:
            digest = None
        if on_progress:
            on_progress()
        return size, path, mtime, digest

    hash_groups: dict[tuple[int, str], list[FileInfo]] = defaultdict(list)
    workers = max_workers or min(32, (os.cpu_count() or 4) * 4)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for size, path, mtime, digest in pool.map(hash_one, all_candidates):
            if digest is None:
                continue
            hash_groups[(size, digest)].append(FileInfo(path=path, mtime=mtime))

    groups = [
        DupGroup(digest=digest, size=size, files=files)
        for (size, digest), files in hash_groups.items()
        if len(files) > 1
    ]
    groups.sort(key=lambda g: g.wasted_bytes, reverse=True)
    return groups


def print_groups(groups: list[DupGroup], console: Console) -> None:
    total_wasted = sum(g.wasted_bytes for g in groups)
    for i, group in enumerate(groups, start=1):
        console.print(
            f"\n[bold]Group {i}[/bold]  {human_size(group.size)} each, "
            f"{len(group.files)} copies  "
            f"([yellow]wastes {human_size(group.wasted_bytes)}[/yellow])"
        )
        for f in sorted(group.files, key=lambda fi: fi.mtime, reverse=True):
            mtime_str = datetime.fromtimestamp(f.mtime).strftime("%Y-%m-%d %H:%M:%S")
            console.print(f"    {mtime_str}  {f.path}")
    console.print(f"\n[bold]{len(groups)} duplicate group(s), {human_size(total_wasted)} reclaimable in total[/bold]")


def interactive_resolve(groups: list[DupGroup], *, yes: bool = False, console: Optional[Console] = None) -> tuple[int, int]:
    """Walk each group, asking which copies to keep, deleting the rest.

    Per group: enter comma-separated indices to KEEP (default: 1, the
    newest), 's' to skip the group untouched, or 'q' to stop entirely.
    Returns (files_deleted, bytes_freed).
    """
    console = console or Console()
    deleted_count = 0
    freed_bytes = 0

    for i, group in enumerate(groups, start=1):
        ranked = sorted(group.files, key=lambda fi: fi.mtime, reverse=True)
        console.print(f"\n[bold]Group {i}/{len(groups)}[/bold]  {human_size(group.size)} each, {len(ranked)} copies")
        for idx, f in enumerate(ranked, start=1):
            mtime_str = datetime.fromtimestamp(f.mtime).strftime("%Y-%m-%d %H:%M:%S")
            console.print(f"  [{idx}] {mtime_str}  {f.path}")

        choice = console.input("Keep which? (comma-separated, default=1=newest, s=skip, q=quit) > ").strip().lower()
        if choice == "q":
            break
        if choice == "s":
            continue

        if not choice:
            keep_indices = {1}
        else:
            try:
                keep_indices = {int(tok) for tok in choice.split(",") if tok.strip()}
            except ValueError:
                console.print("[red]Invalid input, skipping group.[/red]")
                continue

        to_delete = [f for idx, f in enumerate(ranked, start=1) if idx not in keep_indices]
        if not to_delete:
            continue

        if not yes:
            console.print(f"Will delete {len(to_delete)} file(s):")
            for f in to_delete:
                console.print(f"    {f.path}")
            if console.input("Proceed? [y/N] > ").strip().lower() != "y":
                console.print("Skipped.")
                continue

        for f in to_delete:
            try:
                f.path.unlink()
                deleted_count += 1
                freed_bytes += group.size
            except OSError as exc:
                console.print(f"[red]Failed to delete {f.path}: {exc}[/red]")

    return deleted_count, freed_bytes
