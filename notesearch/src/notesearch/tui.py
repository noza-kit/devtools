from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.table import Table

from notesearch.editor import open_in_editor
from notesearch.hybrid import SearchResult

_PAGE_SIZE = 15


def _render(results: list[SearchResult], selected: int) -> Table:
    table = Table(title="notesearch results (↑/↓ move, Enter open in editor, Esc quit)")
    table.add_column("#")
    table.add_column("score")
    table.add_column("source")
    table.add_column("preview")
    for i, r in enumerate(results[:_PAGE_SIZE]):
        marker = "▶" if i == selected else " "
        source = r.metadata.get("source", "")
        preview = r.text.replace("\n", " ").strip()[:80]
        table.add_row(marker, f"{r.combined_score:.2f}", source, preview)
    return table


def run_search_tui(
    results: list[SearchResult],
    editor_command: str,
    console: Optional[Console] = None,
) -> Optional[SearchResult]:
    """Interactive results browser (fzf-style single list, no further
    filtering -- the query itself already narrowed things down): ↑/↓
    to move, Enter to jump straight to the selected chunk's line in the
    configured editor (`editor_command`, default `code -g
    {path}:{line}`), Esc to quit without opening anything. Uses
    `msvcrt` (Windows-only, stdlib) for raw keypress reading, same
    approach as snapclip's history TUI -- no automated test for this
    loop itself (interactive by nature)."""
    import msvcrt

    console = console or Console()
    if not results:
        console.print("該当する結果がありません。")
        return None

    selected = 0
    with Live(_render(results, selected), console=console, auto_refresh=False) as live:
        while True:
            ch = msvcrt.getwch()
            if ch == "\r":
                picked = results[selected]
                source = picked.metadata.get("source")
                line = picked.metadata.get("start_line", 1)
                if source:
                    open_in_editor(editor_command, Path(source), line)
                return picked
            if ch == "\x1b":
                return None
            if ch == "\xe0":
                arrow = msvcrt.getwch()
                if arrow == "H":
                    selected = max(0, selected - 1)
                elif arrow == "P":
                    selected = min(len(results) - 1, selected + 1)

            live.update(_render(results, selected), refresh=True)
