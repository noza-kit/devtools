from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from projarchive import compress, core, scan

app = typer.Typer(
    help="Archive/restore project venvs to save disk space while keeping them reproducible",
    add_completion=True,
)
console = Console(width=120)


@app.callback()
def main() -> None:
    """Archive/restore project venvs to save disk space while keeping them reproducible."""


def _archive_one(project: Path, *, dry_run: bool) -> None:
    try:
        result = core.archive_project(project, dry_run=dry_run)
    except core.AlreadyArchivedError as exc:
        typer.secho(str(exc), fg=typer.colors.YELLOW)
        raise typer.Exit(code=1) from exc
    except core.VenvNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc
    except core.PipFreezeError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED)
        typer.secho("Aborted: venv was not deleted.", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    verb = "[dry-run] would archive" if dry_run else "Archived"
    freed_verb = "would free" if dry_run else "freed"
    typer.secho(f"{verb} {project}", fg=typer.colors.GREEN)
    typer.echo(f"  venv {freed_verb}: {core.human_size(result.venv_size_bytes)} ({result.venv_dir_name})")
    if result.requirements_generated:
        action = "would be generated via `pip freeze`" if dry_run else "generated via `pip freeze`"
        typer.echo(f"  requirements.txt: {action}")
    else:
        typer.echo("  requirements.txt: already exists" if dry_run else "  requirements.txt: already existed")


def _archive_all(parent: Path, *, dry_run: bool) -> None:
    archived = 0
    skipped = 0
    freed_bytes = 0

    for project in core.iter_project_dirs(parent):
        try:
            result = core.archive_project(project, dry_run=dry_run)
        except core.AlreadyArchivedError:
            typer.secho(f"skip {project.name}: already archived", fg=typer.colors.YELLOW)
            skipped += 1
            continue
        except core.VenvNotFoundError:
            typer.secho(f"skip {project.name}: no venv found", fg=typer.colors.YELLOW)
            skipped += 1
            continue
        except core.PipFreezeError as exc:
            typer.secho(f"skip {project.name}: {exc}", fg=typer.colors.RED)
            skipped += 1
            continue

        archived += 1
        freed_bytes += result.venv_size_bytes
        note = "generated" if result.requirements_generated else "existing requirements.txt"
        verb = "[dry-run] would archive" if dry_run else "archived"
        typer.secho(
            f"{verb} {project.name}: {core.human_size(result.venv_size_bytes)} ({note})",
            fg=typer.colors.GREEN,
        )

    total_verb = "would be archived" if dry_run else "archived"
    freed_verb = "would be freed" if dry_run else "freed"
    typer.echo("")
    typer.echo(
        f"{archived} project(s) {total_verb}, {skipped} skipped, "
        f"{core.human_size(freed_bytes)} {freed_verb} total"
    )


@app.command("archive-project")
def archive_project_cmd(
    path: Path = typer.Argument(..., help="Project directory, or parent directory when --all is given"),
    all_projects: bool = typer.Option(
        False, "--all", help="Treat PATH as a parent directory and archive every project directly under it"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be archived without deleting or writing anything"
    ),
) -> None:
    """Delete PATH's venv (after ensuring requirements.txt exists) and mark it archived."""
    if not path.is_dir():
        typer.secho(f"Not a directory: {path}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if all_projects:
        _archive_all(path, dry_run=dry_run)
    else:
        _archive_one(path, dry_run=dry_run)


@app.command("restore-project")
def restore_project_cmd(
    path: Path = typer.Argument(..., help="Project directory containing requirements.txt"),
) -> None:
    """Recreate PATH's venv from requirements.txt (via `uv` if available, else `python -m venv`)."""
    if not path.is_dir():
        typer.secho(f"Not a directory: {path}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    try:
        result = core.restore_project(path)
    except core.RequirementsNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc
    except core.VenvAlreadyExistsError:
        typer.secho(f"{path} is already restored", fg=typer.colors.YELLOW)
        return
    except core.RestoreError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    tool = "uv" if result.used_uv else "python -m venv + pip"
    typer.secho(f"Restored {path}", fg=typer.colors.GREEN)
    typer.echo(f"  venv: {result.venv_dir_name} (via {tool})")
    typer.echo(f"  elapsed: {result.elapsed_seconds:.1f}s")


def _compress_project(
    path: Path,
    *,
    format: str,
    level: str,
    large_file_threshold_mb: int,
    exclude_large_files: Optional[bool],
    dry_run: bool,
) -> None:
    threshold_bytes = large_file_threshold_mb * 1024 * 1024
    large_files = scan.scan_large_files(path, threshold_bytes)

    excluded: list[scan.LargeFile] = []
    if large_files:
        typer.secho(
            f"Found {len(large_files)} file(s) >= {large_file_threshold_mb} MB:", fg=typer.colors.YELLOW
        )
        for lf in large_files:
            typer.echo(f"  {lf.path.relative_to(path)}  ({core.human_size(lf.size_bytes)})")

        if exclude_large_files is None:
            if dry_run:
                exclude_large_files = False
            elif not sys.stdin.isatty():
                typer.secho(
                    "Refusing to prompt in a non-interactive session; pass --exclude-large-files "
                    "or --include-large-files.",
                    fg=typer.colors.RED,
                )
                raise typer.Exit(code=1)
            else:
                exclude_large_files = typer.confirm(
                    "Exclude these from the archive (moved to a sibling *_excluded folder)?"
                )

        if exclude_large_files:
            excluded = large_files
            typer.echo(f"  -> excluding {len(excluded)} file(s)")
        else:
            typer.echo("  -> including them in the archive")

    if dry_run:
        original_size = core.dir_size(path)
        typer.secho(f"[dry-run] would compress {path}", fg=typer.colors.GREEN)
        typer.echo(f"  current size: {core.human_size(original_size)}")
        venv_dir = core.find_venv_dir(path)
        if venv_dir is not None:
            typer.echo(
                f"  venv would be archived first: {venv_dir.name} "
                f"({core.human_size(core.dir_size(venv_dir))})"
            )
        readme_exists = (path / "README.md").exists()
        typer.echo(f"  README.md: {'already exists' if readme_exists else 'would be auto-generated'}")
        typer.echo(f"  format: {format}, compression level: {level}")
        if excluded:
            typer.echo(f"  would exclude {len(excluded)} large file(s)")
        return

    try:
        result = compress.compress_project(
            path, format=format, compression_level=level, excluded_files=excluded
        )
    except compress.ArchiveAlreadyExistsError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc
    except compress.IntegrityCheckError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc
    except core.PipFreezeError as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED)
        typer.secho("Aborted: nothing was compressed or deleted.", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    typer.secho(f"Compressed {result.project} -> {result.archive_path}", fg=typer.colors.GREEN)
    typer.echo(f"  original size: {core.human_size(result.original_size_bytes)}")
    typer.echo(f"  compressed size: {core.human_size(result.compressed_size_bytes)}")
    saved = result.original_size_bytes - result.compressed_size_bytes
    pct = (saved / result.original_size_bytes * 100) if result.original_size_bytes else 0.0
    typer.echo(f"  saved: {core.human_size(saved)} ({pct:.1f}%)")
    if result.venv_stripped:
        typer.echo(
            f"  venv archived first: {result.venv_dir_name} "
            f"({core.human_size(result.venv_size_bytes)} freed)"
        )
    if result.readme_generated:
        typer.echo("  README.md: auto-generated")
    if result.excluded_files:
        typer.echo(f"  excluded {len(result.excluded_files)} large file(s) -> {result.excluded_dir}")


@app.command("compress-project")
def compress_project_cmd(
    path: Path = typer.Argument(..., help="Project directory to compress"),
    format: str = typer.Option("zip", "--format", help="Archive format: zip or tar.gz"),
    compression_level: str = typer.Option(
        "standard", "--compression-level", help="Compression level: standard or max"
    ),
    max_compression: bool = typer.Option(
        False, "--max-compression", help="Shortcut for --compression-level max"
    ),
    large_file_threshold_mb: int = typer.Option(
        500, "--large-file-threshold-mb", help="Files at/above this size (MB) are flagged before compressing"
    ),
    exclude_large_files: Optional[bool] = typer.Option(
        None,
        "--exclude-large-files/--include-large-files",
        help="Decide upfront whether flagged large files are moved aside, instead of prompting",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would happen without changing or deleting anything"
    ),
) -> None:
    """Zip/tar.gz PATH, verify it, then delete the original folder (venv gets archived first)."""
    if not path.is_dir():
        typer.secho(f"Not a directory: {path}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    path = path.resolve()

    if format not in compress.VALID_FORMATS:
        typer.secho(f"Unsupported format: {format} (expected zip or tar.gz)", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    level = "max" if max_compression else compression_level
    if level not in compress.VALID_LEVELS:
        typer.secho(
            f"Unsupported compression level: {level} (expected standard or max)", fg=typer.colors.RED
        )
        raise typer.Exit(code=1)

    _compress_project(
        path,
        format=format,
        level=level,
        large_file_threshold_mb=large_file_threshold_mb,
        exclude_large_files=exclude_large_files,
        dry_run=dry_run,
    )


@app.command("restore-compressed-project")
def restore_compressed_project_cmd(
    archive: Path = typer.Argument(..., help="Path to a .zip or .tar.gz produced by compress-project"),
) -> None:
    """Extract ARCHIVE back to its original location and rebuild its venv if possible."""
    if not archive.is_file():
        typer.secho(f"Not a file: {archive}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    try:
        result = compress.restore_compressed_project(archive)
    except (compress.ArchiveNotFoundError, compress.DestinationExistsError, compress.UnrecognizedArchiveError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    typer.secho(f"Restored {result.project}", fg=typer.colors.GREEN)
    typer.echo(f"  elapsed: {result.elapsed_seconds:.1f}s")
    if result.excluded_restored:
        typer.echo(f"  restored {result.excluded_restored} previously-excluded file(s)")
    if result.venv_attempted:
        if result.venv_rebuilt:
            tool = "uv" if result.used_uv else "python -m venv + pip"
            typer.echo(f"  venv: rebuilt (via {tool})")
        else:
            typer.secho(f"  venv: rebuild failed - {result.venv_error}", fg=typer.colors.YELLOW)
    else:
        typer.echo("  venv: not applicable (no requirements.txt, or a venv was already present)")


@app.command("list-projects")
def list_projects_cmd(
    parent: Path = typer.Argument(..., help="Parent directory containing multiple projects"),
) -> None:
    """List projects directly under PARENT with their venv size, requirements.txt, and archive status."""
    if not parent.is_dir():
        typer.secho(f"Not a directory: {parent}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    statuses = core.list_projects(parent)
    existing_names = {status.name for status in statuses}
    compressed = [c for c in compress.list_compressed(parent) if c.project_name not in existing_names]

    if not statuses and not compressed:
        typer.echo(f"No projects found under {parent}")
        return

    table = Table(title=f"Projects under {parent}")
    table.add_column("Project", overflow="fold")
    table.add_column("Status")
    table.add_column("venv size", justify="right")
    table.add_column("requirements.txt")
    table.add_column("Archive", overflow="fold")
    table.add_column("Compressed size", justify="right")

    rows = [
        (
            status.name,
            status.status,
            core.human_size(status.venv_size_bytes) if status.venv_size_bytes is not None else "-",
            "yes" if status.has_requirements else "no",
            "-",
            "-",
        )
        for status in statuses
    ] + [
        (
            c.project_name,
            "compressed",
            "-",
            "-",
            f"{Path(c.archive_path).name} ({c.compressed_at[:10]})",
            core.human_size(c.compressed_size_bytes),
        )
        for c in compressed
    ]

    for row in sorted(rows, key=lambda r: r[0]):
        table.add_row(*row)

    console.print(table)


if __name__ == "__main__":
    app()
