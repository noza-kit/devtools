from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from devtoolbox.common.config import load_config
from devtoolbox.common.paths import orgdir_log_path
from devtoolbox.orgdir.config import load_orgdir_config
from devtoolbox.orgdir.core import append_log, organize

app = typer.Typer(
    help="Sort files in a directory into subfolders by extension",
    add_completion=True,
)


def _resolve_rules_file(config: Optional[Path]) -> Optional[Path]:
    if config is not None:
        return config.expanduser()
    global_config = load_config()
    if global_config.orgdir.rules_file:
        return Path(global_config.orgdir.rules_file).expanduser()
    return None


@app.command()
def main(
    target: Path = typer.Argument(..., help="Directory to organize"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show planned moves without touching any files"
    ),
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Custom YAML file mapping categories to extensions"
    ),
) -> None:
    """Move files directly inside TARGET into extension-based subfolders (images/, documents/, ...)."""
    if not target.is_dir():
        typer.secho(f"Not a directory: {target}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    rules_file = _resolve_rules_file(config)
    try:
        rules = load_orgdir_config(rules_file)
    except FileNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    result = organize(target, rules, dry_run=dry_run)

    if not result.moved and not result.errors:
        typer.echo(f"Nothing to organize in {target}")
        return

    verb = "[dry-run] would move" if dry_run else "moved"
    for move in result.moved:
        typer.secho(
            f"{verb}: {move.source.name} -> {move.category}/{move.destination.name}",
            fg=typer.colors.GREEN,
        )
    for msg in result.errors:
        typer.secho(f"error: {msg}", fg=typer.colors.RED)

    if not dry_run and result.moved:
        log_path = orgdir_log_path()
        append_log(log_path, target, result.moved)
        typer.secho(f"Logged {len(result.moved)} move(s) to {log_path}", fg=typer.colors.CYAN)

    if result.errors:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
