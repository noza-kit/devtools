from __future__ import annotations

import sys
from typing import Optional

import typer

from devtoolbox.common.paths import snippets_db_path
from devtoolbox.snip.clipboard import ClipboardUnavailableError, read_clipboard, write_clipboard
from devtoolbox.snip.db import (
    SnippetExistsError,
    SnippetNotFoundError,
    add_snippet,
    get_connection,
    get_snippet,
    list_snippets,
    remove_snippet,
    search_snippets,
)

app = typer.Typer(help="Personal snippet manager", add_completion=False)


def _parse_tags(tags: str) -> list[str]:
    return [t.strip() for t in tags.split(",") if t.strip()]


def _format_line(name: str, tags: list[str]) -> str:
    tag_str = f" [{', '.join(tags)}]" if tags else ""
    return f"{name}{tag_str}"


@app.command()
def add(
    name: str = typer.Argument(..., help="Snippet name (unique identifier)"),
    tags: str = typer.Option("", "--tags", "-t", help="Comma separated tags"),
    stdin: bool = typer.Option(False, "--stdin", help="Force reading content from stdin"),
    overwrite: bool = typer.Option(
        False, "--overwrite", "-f", help="Overwrite the snippet if it already exists"
    ),
) -> None:
    """Save a snippet from stdin (if piped) or the clipboard."""
    if stdin or not sys.stdin.isatty():
        content = sys.stdin.read()
    else:
        try:
            content = read_clipboard()
        except ClipboardUnavailableError as exc:
            typer.secho(f"Clipboard unavailable: {exc}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

    content = content.rstrip("\n")
    if not content:
        typer.secho("Nothing to save: content is empty", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    conn = get_connection(snippets_db_path())
    try:
        add_snippet(conn, name, content, _parse_tags(tags), overwrite=overwrite)
    except SnippetExistsError as exc:
        typer.secho(f"{exc} (use --overwrite to replace)", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    finally:
        conn.close()

    typer.secho(f"Saved snippet '{name}'", fg=typer.colors.GREEN)


@app.command(name="list")
def list_cmd(
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter by tag"),
) -> None:
    """List saved snippets, optionally filtered by tag."""
    conn = get_connection(snippets_db_path())
    try:
        snippets = list_snippets(conn, tag=tag)
    finally:
        conn.close()

    if not snippets:
        typer.echo("No snippets found.")
        return

    for s in snippets:
        typer.echo(_format_line(s.name, s.tags))


@app.command()
def get(
    name: str = typer.Argument(..., help="Snippet name"),
    copy: bool = typer.Option(False, "--copy", "-c", help="Copy content to clipboard"),
) -> None:
    """Show a snippet's content."""
    conn = get_connection(snippets_db_path())
    try:
        snippet = get_snippet(conn, name)
    finally:
        conn.close()

    if snippet is None:
        typer.secho(f"Snippet '{name}' not found", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.echo(snippet.content)

    if copy:
        try:
            write_clipboard(snippet.content)
        except ClipboardUnavailableError as exc:
            typer.secho(f"Clipboard unavailable: {exc}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        typer.secho("Copied to clipboard", fg=typer.colors.GREEN)


@app.command()
def search(keyword: str = typer.Argument(..., help="Keyword to search for")) -> None:
    """Search snippets by name, tag, or content."""
    conn = get_connection(snippets_db_path())
    try:
        results = search_snippets(conn, keyword)
    finally:
        conn.close()

    if not results:
        typer.echo("No matches found.")
        return

    for s in results:
        typer.echo(_format_line(s.name, s.tags))


@app.command()
def rm(
    name: str = typer.Argument(..., help="Snippet name"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Delete a snippet."""
    if not yes and not typer.confirm(f"Delete snippet '{name}'?"):
        raise typer.Exit(code=0)

    conn = get_connection(snippets_db_path())
    try:
        remove_snippet(conn, name)
    except SnippetNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)
    finally:
        conn.close()

    typer.secho(f"Removed snippet '{name}'", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
