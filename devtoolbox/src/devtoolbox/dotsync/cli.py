from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from devtoolbox.common.config import load_config
from devtoolbox.common.paths import dotsync_home
from devtoolbox.dotsync.core import link_all, status_all, unlink_all

app = typer.Typer(
    help="Symlink dotfiles from a source repo into your home directory",
    add_completion=True,
)


def _resolve_source(source: Optional[Path]) -> Path:
    if source is not None:
        return source.expanduser()
    config = load_config()
    if config.dotsync.source_dir:
        return Path(config.dotsync.source_dir).expanduser()
    return dotsync_home() / "dotfiles"


def _require_source_dir(source_dir: Path) -> None:
    if not source_dir.is_dir():
        typer.secho(f"Source directory not found: {source_dir}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command()
def link(
    source: Optional[Path] = typer.Option(
        None, "--source", "-s", help="Dotfiles source directory (default: ~/dotfiles or config)"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Back up (to <name>.bak) and replace conflicting files"
    ),
) -> None:
    """Symlink every top-level dotfile/dotdir from the source into $HOME."""
    source_dir = _resolve_source(source)
    _require_source_dir(source_dir)

    result = link_all(source_dir, dotsync_home(), force=force)

    for path in result.linked:
        typer.secho(f"linked: {path}", fg=typer.colors.GREEN)
    for path in result.already_linked:
        typer.secho(f"already linked: {path}", fg=typer.colors.CYAN)
    for path in result.backed_up:
        typer.secho(f"backed up existing file to: {path}", fg=typer.colors.YELLOW)
    for path in result.skipped_conflicts:
        typer.secho(f"conflict (use --force to replace): {path}", fg=typer.colors.YELLOW)
    for msg in result.errors:
        typer.secho(f"error: {msg}", fg=typer.colors.RED)

    if not any(
        [result.linked, result.already_linked, result.skipped_conflicts, result.errors]
    ):
        typer.echo(f"No dotfiles found in {source_dir} (entries must start with '.')")

    if result.errors:
        raise typer.Exit(code=1)


@app.command()
def status(
    source: Optional[Path] = typer.Option(None, "--source", "-s", help="Dotfiles source directory"),
) -> None:
    """Show the link status of every dotfile in the source directory."""
    source_dir = _resolve_source(source)
    _require_source_dir(source_dir)

    statuses = status_all(source_dir, dotsync_home())
    if not statuses:
        typer.echo(f"No dotfiles found in {source_dir} (entries must start with '.')")
        return

    colors = {
        "linked": typer.colors.GREEN,
        "missing": typer.colors.YELLOW,
        "conflict": typer.colors.RED,
    }
    for name, state in statuses:
        typer.secho(f"{name}: {state}", fg=colors[state])


@app.command()
def unlink(
    source: Optional[Path] = typer.Option(None, "--source", "-s", help="Dotfiles source directory"),
) -> None:
    """Remove symlinks created by `dotsync link`, restoring any backups."""
    source_dir = _resolve_source(source)
    _require_source_dir(source_dir)

    result = unlink_all(source_dir, dotsync_home())

    for path in result.removed:
        typer.secho(f"unlinked: {path}", fg=typer.colors.GREEN)
    for path in result.restored:
        typer.secho(f"restored backup: {path}", fg=typer.colors.CYAN)
    for msg in result.errors:
        typer.secho(f"skipped: {msg}", fg=typer.colors.YELLOW)

    if not result.removed and not result.errors:
        typer.echo("Nothing to unlink.")


if __name__ == "__main__":
    app()
