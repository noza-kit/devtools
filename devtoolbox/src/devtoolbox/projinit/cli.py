from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from devtoolbox.projinit.config import load_languages
from devtoolbox.projinit.core import init_project

app = typer.Typer(
    help="Scaffold a new project: git init, .gitignore, README.md",
    add_completion=False,
)


@app.command()
def main(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Project name"),
    lang: Optional[str] = typer.Option(
        None, "--lang", "-l", help="Language/framework key (e.g. python, node, generic)"
    ),
    description: str = typer.Option(
        "", "--description", "-d", help="Short project description for the README"
    ),
    directory: Optional[Path] = typer.Option(
        None, "--dir", help="Target directory (default: ./<name>)"
    ),
    git: bool = typer.Option(True, "--git/--no-git", help="Run `git init`"),
) -> None:
    """Interactively (or via flags) scaffold a new project."""
    languages = load_languages()

    if name is None:
        name = typer.prompt("Project name")

    if lang is None:
        choices = ", ".join(sorted(languages))
        lang = typer.prompt(f"Language [{choices}]")

    if lang not in languages:
        available = ", ".join(sorted(languages))
        typer.secho(f"Unknown language '{lang}'. Available: {available}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if not description:
        description = typer.prompt("Description", default="", show_default=False)

    language = languages[lang]
    target_dir = directory if directory is not None else Path.cwd() / name

    result = init_project(
        target_dir=target_dir,
        project_name=name,
        description=description,
        language=language,
        do_git_init=git,
    )

    typer.secho(f"Project directory: {target_dir}", fg=typer.colors.CYAN)
    if result.git_initialized:
        typer.secho("git init: done", fg=typer.colors.GREEN)
    for path in result.created:
        typer.secho(f"created: {path}", fg=typer.colors.GREEN)
    for path in result.skipped:
        typer.secho(f"skipped (already exists): {path}", fg=typer.colors.YELLOW)


if __name__ == "__main__":
    app()
