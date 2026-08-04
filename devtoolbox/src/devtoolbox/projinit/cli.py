from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

import typer

from devtoolbox.common.config import load_config
from devtoolbox.projinit.config import UnknownLicenseError, load_languages
from devtoolbox.projinit.core import init_project

app = typer.Typer(
    help="Scaffold a new project: git init, .gitignore, README.md, LICENSE",
    add_completion=True,
)


def _git_user_name() -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    name = out.stdout.strip()
    return name or None


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
    run_init_command: bool = typer.Option(
        True,
        "--run-init-command/--no-run-init-command",
        help="Run the language's init command (e.g. venv creation, `npm init`)",
    ),
    license: Optional[str] = typer.Option(
        None, "--license", "-L", help="License key (mit, apache-2.0). Omit for no LICENSE file."
    ),
    author: Optional[str] = typer.Option(
        None, "--author", "-a", help="Copyright holder name used in the LICENSE file"
    ),
) -> None:
    """Interactively (or via flags) scaffold a new project."""
    config = load_config()
    languages = load_languages()

    if name is None:
        name = typer.prompt("Project name")

    if lang is None:
        lang = config.projinit.default_lang
    if lang is None:
        choices = ", ".join(sorted(languages))
        lang = typer.prompt(f"Language [{choices}]")

    if lang not in languages:
        available = ", ".join(sorted(languages))
        typer.secho(f"Unknown language '{lang}'. Available: {available}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if not description:
        description = typer.prompt("Description", default="", show_default=False)

    if license is None:
        license = config.projinit.default_license

    if author is None:
        author = config.projinit.default_author or _git_user_name() or "Unknown"

    language = languages[lang]
    target_dir = directory if directory is not None else Path.cwd() / name

    try:
        result = init_project(
            target_dir=target_dir,
            project_name=name,
            description=description,
            language=language,
            do_git_init=git,
            do_init_command=run_init_command,
            license_key=license,
            author=author,
        )
    except UnknownLicenseError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho(f"Project directory: {target_dir}", fg=typer.colors.CYAN)
    if result.git_initialized:
        typer.secho("git init: done", fg=typer.colors.GREEN)
    if result.command_run:
        typer.secho(f"ran: {result.command_run}", fg=typer.colors.GREEN)
    if result.command_error:
        typer.secho(f"init command failed: {result.command_error}", fg=typer.colors.YELLOW)
    for path in result.created:
        typer.secho(f"created: {path}", fg=typer.colors.GREEN)
    for path in result.skipped:
        typer.secho(f"skipped (already exists): {path}", fg=typer.colors.YELLOW)


if __name__ == "__main__":
    app()
