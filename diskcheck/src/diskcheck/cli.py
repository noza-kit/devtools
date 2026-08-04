from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from confload import ConfigError
from rich.console import Console
from rich.table import Table

from diskcheck.config import load_stale_extensions, normalize_extension
from diskcheck.dupes import find_duplicate_groups, interactive_resolve, print_groups
from diskcheck.fsutils import human_size, progress_spinner
from diskcheck.scan import interactive_browse, render_tree, scan_tree
from diskcheck.stale import find_stale_files

app = typer.Typer(
    help="diskcheck: storage usage scan, duplicate file detection, and stale installer cleanup candidates",
    add_completion=True,
)
console = Console()


@app.callback()
def main() -> None:
    """diskcheck: storage usage scan, duplicate file detection, and stale installer cleanup candidates."""


@app.command()
def scan(
    path: Path = typer.Argument(..., help="Directory to scan"),
    top: int = typer.Option(20, "--top", help="Show the top N largest entries per level"),
    depth: int = typer.Option(2, "--depth", help="How many levels deep to display"),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON instead of the tree view"),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Drill down into subfolders interactively instead of printing a tree"
    ),
) -> None:
    """Rank folders/files under PATH by size."""
    if not path.exists():
        typer.secho(f"Path not found: {path}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    with progress_spinner(f"Scanning {path}") as tick:
        root = scan_tree(path, on_entry=lambda _node: tick())

    if json_output:
        typer.echo(json.dumps(root.to_dict(top=top, max_depth=depth), ensure_ascii=False, indent=2))
        return

    if interactive:
        interactive_browse(root, top=top, console=console)
        return

    console.print(render_tree(root, top=top, max_depth=depth))


@app.command()
def dupes(
    path: Path = typer.Argument(..., help="Directory to scan for duplicate files"),
    min_size: int = typer.Option(1, "--min-size", help="Ignore files smaller than this many bytes"),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON instead of a text listing"),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Interactively choose which copy to keep and delete the rest"
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Skip per-group deletion confirmation (only applies with --interactive)"
    ),
) -> None:
    """Find duplicate files under PATH by content (SHA256), grouped by identical hash.

    Lists duplicate groups only (dry run) unless --interactive is given.
    """
    if not path.is_dir():
        typer.secho(f"Not a directory: {path}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    with progress_spinner(f"Hashing candidates in {path}") as tick:
        groups = find_duplicate_groups(path, min_size=min_size, on_progress=tick)

    if json_output:
        typer.echo(json.dumps([g.to_dict() for g in groups], ensure_ascii=False, indent=2))
        return

    if not groups:
        typer.echo("No duplicate files found.")
        return

    print_groups(groups, console)

    if interactive:
        deleted, freed = interactive_resolve(groups, yes=yes, console=console)
        console.print(f"\n[bold green]Deleted {deleted} file(s), freed {human_size(freed)}[/bold green]")
    else:
        console.print("\n(dry run: no files deleted. Re-run with --interactive to select files to delete.)")


@app.command()
def stale(
    path: Path = typer.Argument(..., help="Directory to scan for stale installers/temp files"),
    older_than: int = typer.Option(180, "--older-than", help="Flag files not accessed in at least this many days"),
    extensions: Optional[str] = typer.Option(
        None, "--extensions", help="Comma-separated extension list, overrides --config/defaults, e.g. .dmg,.exe"
    ),
    config: Optional[Path] = typer.Option(
        None, "--config", help="YAML/JSON config file with an `extensions` list (defaults to a built-in list)"
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON instead of a table"),
) -> None:
    """Find old installers/temp files (by extension and last-access time) under PATH.

    Presentation only: nothing is ever deleted by this command.
    """
    if not path.is_dir():
        typer.secho(f"Not a directory: {path}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if extensions:
        ext_list = [normalize_extension(e) for e in extensions.split(",") if e.strip()]
    else:
        try:
            ext_list = load_stale_extensions(config)
        except ConfigError as exc:
            typer.secho(str(exc), fg=typer.colors.RED)
            raise typer.Exit(code=1)

    with progress_spinner(f"Scanning {path}") as tick:
        results = find_stale_files(path, extensions=ext_list, older_than_days=older_than, on_progress=tick)

    if json_output:
        typer.echo(json.dumps([f.to_dict() for f in results], ensure_ascii=False, indent=2))
        return

    if not results:
        typer.echo(f"No stale files found (extensions: {', '.join(ext_list)}; older than {older_than} days).")
        return

    table = Table(title=f"Stale files under {path} (not accessed in {older_than}+ days)")
    table.add_column("Size", justify="right")
    table.add_column("Last accessed")
    table.add_column("Path", overflow="fold")
    for f in results:
        table.add_row(human_size(f.size), f.to_dict()["last_accessed"], str(f.path))
    console.print(table)

    total = sum(f.size for f in results)
    console.print(
        f"\n{len(results)} file(s), {human_size(total)} total. "
        "Listing only - review and delete manually."
    )


if __name__ == "__main__":
    app()
