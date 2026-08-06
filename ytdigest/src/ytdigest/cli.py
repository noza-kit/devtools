from __future__ import annotations

import logging
import sys
from pathlib import Path

import typer

for _stream in (sys.stdout, sys.stderr):
    # On Windows, stdout/stderr often default to the system codepage rather
    # than UTF-8, which mangles non-ASCII text (Japanese channel/video titles)
    # when printed to a UTF-8 terminal.
    if hasattr(_stream, "reconfigure") and (_stream.encoding or "").lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8")

from ytdigest import batch
from ytdigest.config import ConfigError, load_channels, load_secrets
from ytdigest.db import Database

app = typer.Typer(
    help="Daily YouTube/Twitch new-content digest posted to Discord, run from GitHub Actions",
    add_completion=True,
)


@app.command()
def run(
    channels: Path = typer.Option(
        Path("channels.yaml"), "--channels", help="YAML file listing watched YouTube/Twitch channels"
    ),
    db_path: Path = typer.Option(
        Path("data/state.db"), "--db", help="SQLite state file, persisted across runs"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
) -> None:
    """Run one full daily batch: read dismiss replies, detect ended live streams
    (converting them to VODs), fetch new YouTube/Twitch content, notify the
    new-content channel, and archive undismissed items that have gone stale."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )

    try:
        channels_obj = load_channels(channels)
        secrets_obj = load_secrets()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)

    database = Database(db_path)
    try:
        batch.run(database, channels_obj, secrets_obj)
    finally:
        database.close()

    typer.secho("ytdigest batch run complete.", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
