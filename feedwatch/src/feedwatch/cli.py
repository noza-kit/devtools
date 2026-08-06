from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from confload import load_config
from rich.console import Console
from rich.table import Table

from feedwatch.db import DuplicateWatchError, WatchNotFoundError, add_watch, connect, list_watches, remove_watch
from feedwatch.feeds import normalize_feed_source
from feedwatch.poller import DEFAULT_INTERVAL_SECONDS, run_forever

app = typer.Typer(
    help="feedwatch: watch RSS/Atom feeds (e.g. YouTube channels) and Twitch channels for new items, "
    "notifying via notify",
    add_completion=True,
)
console = Console()


@app.callback()
def main() -> None:
    """feedwatch: watch RSS/Atom feeds and Twitch channels for new items, notifying via notify."""


def _parse_tags(tags: str) -> list[str]:
    return [t.strip() for t in tags.split(",") if t.strip()]


@app.command()
def add(
    url: str = typer.Argument(
        ..., help="RSS/Atom feed URL (e.g. a YouTube channel feed), or a bare YouTube channel ID (UCxxxx...)"
    ),
    name: str = typer.Option(..., "--name", help="Display name for this watch"),
    tags: str = typer.Option("", "--tags", help="Comma-separated tags, e.g. youtube"),
) -> None:
    """Register an RSS/Atom feed to watch for new entries."""
    source = normalize_feed_source(url)
    with connect() as conn:
        try:
            watch = add_watch(conn, kind="rss", source=source, name=name, tags=_parse_tags(tags))
        except DuplicateWatchError as exc:
            typer.secho(str(exc), fg=typer.colors.RED)
            raise typer.Exit(code=1)
    typer.secho(f"Added watch #{watch.id}: {watch.name} ({watch.source})", fg=typer.colors.GREEN)


@app.command("add-twitch")
def add_twitch(
    channel_login: str = typer.Argument(..., help="Twitch channel login (the name in twitch.tv/<login>)"),
    name: str = typer.Option(..., "--name", help="Display name for this watch"),
    tags: str = typer.Option("", "--tags", help="Comma-separated tags, e.g. twitch"),
) -> None:
    """Register a Twitch channel to watch for stream starts (via the Twitch API, no RSS available)."""
    with connect() as conn:
        try:
            watch = add_watch(
                conn, kind="twitch", source=channel_login.strip().lower(), name=name, tags=_parse_tags(tags)
            )
        except DuplicateWatchError as exc:
            typer.secho(str(exc), fg=typer.colors.RED)
            raise typer.Exit(code=1)
    typer.secho(f"Added watch #{watch.id}: {watch.name} (twitch.tv/{watch.source})", fg=typer.colors.GREEN)


@app.command("list")
def list_cmd() -> None:
    """List all registered watches."""
    with connect() as conn:
        watches = list_watches(conn)
    if not watches:
        typer.echo("No watches registered.")
        return

    table = Table("ID", "Kind", "Name", "Source", "Tags")
    for w in watches:
        table.add_row(str(w.id), w.kind, w.name, w.source, w.tags)
    console.print(table)


@app.command()
def remove(watch_id: int = typer.Argument(..., help="Watch ID (see `feedwatch list`)")) -> None:
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
        DEFAULT_INTERVAL_SECONDS, "--interval", help="Polling interval in seconds (default 600 = 10 min)"
    ),
    channels: str = typer.Option(
        "desktop", "--channels", help="Comma-separated notify channels, e.g. desktop,discord,line"
    ),
    config: Optional[Path] = typer.Option(
        None, "--config", help="confload YAML/JSON config file for notify webhook / Twitch credentials"
    ),
) -> None:
    """Poll every registered watch on a loop, notifying on new items/streams. Ctrl+C to stop."""
    channel_list = _parse_tags(channels)
    config_obj = load_config(config) if config is not None else None

    with connect() as conn:
        count = len(list_watches(conn))
    if count == 0:
        typer.secho("No watches registered. Use `feedwatch add` / `feedwatch add-twitch` first.", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)

    typer.echo(f"Watching {count} feed(s)/channel(s), checking every {interval}s. Ctrl+C to stop.")
    try:
        run_forever(interval_seconds=interval, channels=channel_list, notify_config=config_obj)
    except KeyboardInterrupt:
        typer.echo("Stopped.")


if __name__ == "__main__":
    app()
