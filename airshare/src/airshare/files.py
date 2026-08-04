from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileEntry:
    name: str
    size: int
    modified: float


def list_files(directory: Path) -> list[FileEntry]:
    """List regular files directly inside `directory`, newest first."""
    entries = []
    for path in directory.iterdir():
        if path.is_file():
            stat = path.stat()
            entries.append(FileEntry(name=path.name, size=stat.st_size, modified=stat.st_mtime))
    entries.sort(key=lambda entry: entry.modified, reverse=True)
    return entries


def resolve_download_path(directory: Path, filename: str) -> Path:
    """Resolve `filename` to a real file inside `directory`, rejecting path traversal."""
    safe_name = Path(filename).name
    if not safe_name or safe_name in {".", ".."}:
        raise ValueError(f"Invalid filename: {filename!r}")

    base = directory.resolve()
    path = (base / safe_name).resolve()
    if not path.is_relative_to(base):
        raise ValueError(f"Invalid filename: {filename!r}")
    if not path.is_file():
        raise FileNotFoundError(filename)
    return path


def save_upload(directory: Path, filename: str, content: bytes) -> Path:
    """Save `content` under `directory` using the basename of `filename`, avoiding collisions."""
    safe_name = Path(filename).name
    if not safe_name or safe_name in {".", ".."}:
        raise ValueError(f"Invalid filename: {filename!r}")

    destination = _avoid_collision(directory / safe_name)
    destination.write_bytes(content)
    return destination


def _avoid_collision(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    counter = 1
    candidate = path
    while candidate.exists():
        candidate = path.with_name(f"{stem} ({counter}){suffix}")
        counter += 1
    return candidate
