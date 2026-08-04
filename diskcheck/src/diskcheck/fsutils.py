from __future__ import annotations

from contextlib import contextmanager
from typing import Callable, Iterator

from rich.progress import Progress, SpinnerColumn, TextColumn

_UNITS = ("B", "KB", "MB", "GB", "TB", "PB")


def human_size(num_bytes: float) -> str:
    """Format a byte count as a human-readable string, e.g. `1.23 GB`."""
    size = float(num_bytes)
    for unit in _UNITS:
        if unit == "B":
            if size < 1024:
                return f"{size:.0f} {unit}"
        elif size < 1024 or unit == _UNITS[-1]:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} {_UNITS[-1]}"


@contextmanager
def progress_spinner(description: str, *, every: int = 200) -> Iterator[Callable[[], None]]:
    """Context manager yielding a callback to invoke once per item processed.

    Renders a transient spinner with a running count, throttled to update
    every `every` calls so it doesn't slow down fast scans.
    """
    count = {"n": 0}
    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task(f"{description}...", total=None)

        def tick() -> None:
            count["n"] += 1
            if count["n"] % every == 0:
                progress.update(task, description=f"{description}... {count['n']} items")

        yield tick
