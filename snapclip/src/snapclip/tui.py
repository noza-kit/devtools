from __future__ import annotations

from typing import Callable, Optional

from rich.console import Console
from rich.live import Live
from rich.table import Table

from snapclip.history import HistoryEntry, filter_entries

_PAGE_SIZE = 15


def _render(entries: list[HistoryEntry], query: str, selected: int) -> Table:
    table = Table(title=f"snapclip history  (search: {query!r} — type to filter, ↑/↓ move, Enter select, Esc quit)")
    table.add_column("#")
    table.add_column("when")
    table.add_column("preview")
    for i, entry in enumerate(entries[:_PAGE_SIZE]):
        marker = "▶" if i == selected else " "
        table.add_row(marker, entry.created_at.split("T")[0] + " " + entry.created_at.split("T")[1][:8], entry.preview())
    return table


def run_history_tui(
    entries: list[HistoryEntry],
    on_select: Callable[[HistoryEntry], None],
    console: Optional[Console] = None,
) -> Optional[HistoryEntry]:
    """Interactive incremental-search picker over `entries`
    (fzf-style): type to filter, arrow keys to move, Enter to call
    `on_select` with the highlighted entry, Esc to quit without
    selecting. Uses `msvcrt` (Windows-only, stdlib) for raw keypress
    reading — there is no automated test for this loop itself (it's
    interactive by nature); `filter_entries()` in history.py, which
    does the actual filtering, is unit tested directly instead."""
    import msvcrt

    console = console or Console()
    query = ""
    selected = 0
    filtered = filter_entries(entries, query)

    with Live(_render(filtered, query, selected), console=console, auto_refresh=False) as live:
        while True:
            ch = msvcrt.getwch()
            if ch == "\r":  # Enter
                if filtered:
                    picked = filtered[selected]
                    on_select(picked)
                    return picked
                continue
            if ch == "\x1b":  # Esc
                return None
            if ch == "\x08":  # Backspace
                query = query[:-1]
            elif ch == "\xe0":  # arrow-key prefix on Windows
                arrow = msvcrt.getwch()
                if arrow == "H":  # up
                    selected = max(0, selected - 1)
                elif arrow == "P":  # down
                    selected = min(max(0, len(filtered) - 1), selected + 1)
                live.update(_render(filtered, query, selected), refresh=True)
                continue
            elif ch.isprintable():
                query += ch

            filtered = filter_entries(entries, query)
            selected = min(selected, max(0, len(filtered) - 1))
            live.update(_render(filtered, query, selected), refresh=True)
