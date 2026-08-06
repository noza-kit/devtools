from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from confload import load_config
from rich.console import Console
from rich.table import Table

from sitewatch.db import (
    DEFAULT_MIN_INTERVAL_SECONDS,
    DuplicateWatchError,
    WatchNotFoundError,
    add_watch,
    connect,
    list_watches,
    remove_watch,
)
from sitewatch.poller import DEFAULT_INTERVAL_SECONDS, run_forever

app = typer.Typer(
    help="sitewatch: watch a CSS-selected element on a page for changes, notifying via notify",
    add_completion=True,
)
console = Console()


@app.callback()
def main() -> None:
    """sitewatch: watch a CSS-selected element on a page for changes, notifying via notify."""


def _parse_channels(channels: str) -> list[str]:
    return [c.strip() for c in channels.split(",") if c.strip()]


@app.command()
def add(
    url: str = typer.Argument(..., help="Page URL to watch"),
    selector: str = typer.Option(..., "--selector", help="CSS selector for the element to watch"),
    name: str = typer.Option(..., "--name", help="Display name for this watch"),
    min_interval: int = typer.Option(
        DEFAULT_MIN_INTERVAL_SECONDS,
        "--min-interval",
        help="Minimum seconds between checks for this site (default 1800 = 30 min)",
    ),
) -> None:
    """Register a page + CSS selector to watch for content changes."""
    with connect() as conn:
        try:
            watch = add_watch(conn, url=url, selector=selector, name=name, min_interval_sec=min_interval)
        except DuplicateWatchError as exc:
            typer.secho(str(exc), fg=typer.colors.RED)
            raise typer.Exit(code=1)
    typer.secho(f"Added watch #{watch.id}: {watch.name} ({watch.url} [{watch.selector}])", fg=typer.colors.GREEN)


@app.command("list")
def list_cmd() -> None:
    """List all registered watches."""
    with connect() as conn:
        watches = list_watches(conn)
    if not watches:
        typer.echo("No watches registered.")
        return

    table = Table("ID", "Name", "URL", "Selector", "Min Interval", "Last Checked")
    for w in watches:
        table.add_row(
            str(w.id), w.name, w.url, w.selector, f"{w.min_interval_sec}s", w.last_checked_at or "(never)"
        )
    console.print(table)


@app.command()
def remove(watch_id: int = typer.Argument(..., help="Watch ID (see `sitewatch list`)")) -> None:
    """Remove a registered watch."""
    with connect() as conn:
        try:
            remove_watch(conn, watch_id)
        except WatchNotFoundError as exc:
            typer.secho(str(exc), fg=typer.colors.RED)
            raise typer.Exit(code=1)
    typer.secho(f"Removed watch #{watch_id}", fg=typer.colors.GREEN)


@app.command()
def start(
    interval: int = typer.Option(
        DEFAULT_INTERVAL_SECONDS,
        "--interval",
        help="Loop tick in seconds (default 1800 = 30 min). Each watch is only actually "
        "re-checked once its own --min-interval has elapsed.",
    ),
    channels: str = typer.Option(
        "desktop", "--channels", help="Comma-separated notify channels, e.g. desktop,discord,line"
    ),
    config: Optional[Path] = typer.Option(
        None, "--config", help="confload YAML/JSON config file for notify webhook credentials"
    ),
) -> None:
    """Poll every registered watch on a loop, notifying on content changes. Ctrl+C to stop."""
    channel_list = _parse_channels(channels)
    config_obj = load_config(config) if config is not None else None

    with connect() as conn:
        count = len(list_watches(conn))
    if count == 0:
        typer.secho("No watches registered. Use `sitewatch add` first.", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)

    typer.echo(f"Watching {count} site(s), checking every {interval}s (per-watch minimum interval applies). Ctrl+C to stop.")
    try:
        run_forever(interval_seconds=interval, channels=channel_list, notify_config=config_obj)
    except KeyboardInterrupt:
        typer.echo("Stopped.")


if __name__ == "__main__":
    app()
