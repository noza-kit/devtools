from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from batchimg.discovery import classify, find_files
from batchimg.io_utils import ImageReadError, load_image, save_image
from batchimg.naming import render_filename
from batchimg.resize import resize_image
from batchimg.video import VideoReadError, process_video


@dataclass
class Options:
    resize: Optional[tuple[int, int]] = None
    keep_aspect: bool = True
    rename_template: Optional[str] = None
    start: int = 1
    digits: int = 4
    date_format: str = "%Y%m%d"
    trim_start: Optional[float] = None
    trim_end: Optional[float] = None


@dataclass
class PlannedItem:
    source: Path
    destination: Path
    kind: str  # "image" | "video"


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


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


def plan(
    source_dir: Path,
    output_dir: Path,
    options: Options,
    *,
    patterns: Optional[list[str]] = None,
    recursive: bool = False,
) -> list[PlannedItem]:
    """Compute what would be processed, without touching the filesystem."""
    files = find_files(source_dir, patterns=patterns, recursive=recursive)
    output_dir_resolved = output_dir.resolve()
    # Only exclude the output subtree when it's nested inside source_dir (e.g. the
    # default SOURCE_DIR/batchimg_out) - not for --in-place, where output_dir IS
    # source_dir and every file legitimately belongs in the plan.
    exclude_output = output_dir_resolved != source_dir.resolve()

    items: list[PlannedItem] = []
    reserved: set[Path] = set()
    index = options.start
    for f in files:
        if exclude_output and _is_within(f.resolve(), output_dir_resolved):
            continue
        kind = classify(f)
        if kind is None:
            continue

        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        name = render_filename(
            f, index, options.rename_template,
            mtime=mtime, digits=options.digits, date_format=options.date_format,
        )
        rel_dir = f.relative_to(source_dir).parent
        candidate = output_dir / rel_dir / name
        if candidate.resolve() == f.resolve():
            # --in-place with no rename: the file's own path is not a "conflict".
            destination = candidate
        else:
            destination = _resolve_conflict(candidate, reserved)
        reserved.add(destination)

        items.append(PlannedItem(source=f, destination=destination, kind=kind))
        index += 1

    return items


def execute(items: list[PlannedItem], options: Options) -> tuple[int, list[str]]:
    """Run the resize/trim/rename operations for `items`.

    Each output is written to a temporary file first and atomically moved into
    place, so a source and destination that happen to be the same path
    (--in-place) are never read and written to concurrently.
    Returns (processed_count, error_messages).
    """
    processed = 0
    errors: list[str] = []

    for item in items:
        item.destination.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(suffix=item.destination.suffix, dir=str(item.destination.parent))
        os.close(fd)
        tmp_path = Path(tmp_name)

        try:
            if item.kind == "image":
                if options.resize is None:
                    shutil.copy2(item.source, tmp_path)
                else:
                    image = load_image(item.source)
                    image = resize_image(image, *options.resize, options.keep_aspect)
                    save_image(tmp_path, image)
            else:
                needs_processing = (
                    options.resize is not None
                    or options.trim_start is not None
                    or options.trim_end is not None
                )
                if not needs_processing:
                    shutil.copy2(item.source, tmp_path)
                else:
                    process_video(
                        item.source, tmp_path,
                        target_size=options.resize, keep_aspect=options.keep_aspect,
                        trim_start=options.trim_start, trim_end=options.trim_end,
                    )
            os.replace(tmp_path, item.destination)
        except (ImageReadError, VideoReadError) as exc:
            tmp_path.unlink(missing_ok=True)
            errors.append(f"{item.source}: {exc}")
            continue

        processed += 1

    return processed, errors
