from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from projarchive import core

app = typer.Typer(
    help="Archive/restore project venvs to save disk space while keeping them reproducible",
    add_completion=True,
)
console = Console()


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


@app.command("list-projects")
def list_projects_cmd(
    parent: Path = typer.Argument(..., help="Parent directory containing multiple projects"),
) -> None:
    """List projects directly under PARENT with their venv size, requirements.txt, and archive status."""
    if not parent.is_dir():
        typer.secho(f"Not a directory: {parent}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    statuses = core.list_projects(parent)
    if not statuses:
        typer.echo(f"No projects found under {parent}")
        return

    table = Table(title=f"Projects under {parent}")
    table.add_column("Project")
    table.add_column("Status")
    table.add_column("venv size", justify="right")
    table.add_column("requirements.txt")

    for status in statuses:
        table.add_row(
            status.name,
            status.status,
            core.human_size(status.venv_size_bytes) if status.venv_size_bytes is not None else "-",
            "yes" if status.has_requirements else "no",
        )

    console.print(table)


if __name__ == "__main__":
    app()
