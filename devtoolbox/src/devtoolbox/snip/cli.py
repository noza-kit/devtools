from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

import typer

from devtoolbox.common.config import load_config
from devtoolbox.common.paths import snippets_db_path
from devtoolbox.snip.clipboard import ClipboardUnavailableError, read_clipboard, write_clipboard
from devtoolbox.snip.db import (
    SnippetExistsError,
    SnippetNotFoundError,
    add_snippet,
    all_tags,
    get_connection,
    get_snippet,
    list_snippets,
    remove_snippet,
    search_snippets,
)

app = typer.Typer(help="Personal snippet manager", add_completion=True)


def _parse_tags(tags: str) -> list[str]:
    return [t.strip() for t in tags.split(",") if t.strip()]


def _merge_with_default_tags(tags: list[str]) -> list[str]:
    config = load_config()
    merged = list(tags)
    for tag in config.snip.default_tags:
        if tag not in merged:
            merged.append(tag)
    return merged


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

    tag_list = _merge_with_default_tags(_parse_tags(tags))

    conn = get_connection(snippets_db_path())
    try:
        add_snippet(conn, name, content, tag_list, overwrite=overwrite)
    except SnippetExistsError as exc:
        typer.secho(f"{exc} (use --overwrite to replace)", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    finally:
        conn.close()

    typer.secho(f"Saved snippet '{name}'", fg=typer.colors.GREEN)


@app.command()
def edit(
    name: str = typer.Argument(..., help="Snippet name"),
    tags: Optional[str] = typer.Option(
        None, "--tags", "-t", help="Replace tags (comma separated). Omit to keep existing tags."
    ),
) -> None:
    """Open a snippet in $EDITOR (or $VISUAL) and save the changes."""
    conn = get_connection(snippets_db_path())
    try:
        snippet = get_snippet(conn, name)
        if snippet is None:
            typer.secho(f"Snippet '{name}' not found", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
        if not editor:
            editor = "notepad" if os.name == "nt" else "vi"

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(snippet.content)
            tmp_path = Path(tmp.name)

        try:
            subprocess.run([editor, str(tmp_path)], check=True)
            new_content = tmp_path.read_text(encoding="utf-8").rstrip("\n")
        finally:
            tmp_path.unlink(missing_ok=True)

        if not new_content:
            typer.secho("Aborted: edited content is empty", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        new_tags = _parse_tags(tags) if tags is not None else snippet.tags
        add_snippet(conn, name, new_content, new_tags, overwrite=True)
    finally:
        conn.close()

    typer.secho(f"Updated snippet '{name}'", fg=typer.colors.GREEN)


@app.command(name="list")
def list_cmd(
    tag: List[str] = typer.Option(
        [], "--tag", "-t", help="Filter by tag (repeatable; a snippet must have all given tags)"
    ),
) -> None:
    """List saved snippets, optionally filtered by tag."""
    conn = get_connection(snippets_db_path())
    try:
        snippets = list_snippets(conn, tags=tag or None)
    finally:
        conn.close()

    if not snippets:
        typer.echo("No snippets found.")
        return

    for s in snippets:
        typer.echo(_format_line(s.name, s.tags))


@app.command()
def tags() -> None:
    """List all tags currently in use, with snippet counts."""
    conn = get_connection(snippets_db_path())
    try:
        counts = all_tags(conn)
    finally:
        conn.close()

    if not counts:
        typer.echo("No tags found.")
        return

    for tag_name, count in sorted(counts.items()):
        typer.echo(f"{tag_name} ({count})")


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


@app.command()
def export(
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output file (default: print to stdout)"
    ),
) -> None:
    """Export all snippets as JSON."""
    conn = get_connection(snippets_db_path())
    try:
        snippets = list_snippets(conn)
    finally:
        conn.close()

    data = [
        {
            "name": s.name,
            "content": s.content,
            "tags": s.tags,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        }
        for s in snippets
    ]
    text = json.dumps(data, ensure_ascii=False, indent=2)

    if output is not None:
        output.write_text(text, encoding="utf-8")
        typer.secho(f"Exported {len(data)} snippet(s) to {output}", fg=typer.colors.GREEN)
    else:
        typer.echo(text)


@app.command(name="import")
def import_cmd(
    input_file: Path = typer.Argument(..., help="JSON file previously produced by `snip export`"),
    overwrite: bool = typer.Option(
        False, "--overwrite", "-f", help="Overwrite existing snippets with the same name"
    ),
) -> None:
    """Import snippets from a JSON file produced by `snip export`."""
    data = json.loads(input_file.read_text(encoding="utf-8"))

    conn = get_connection(snippets_db_path())
    imported = 0
    skipped = 0
    try:
        for entry in data:
            existing = get_snippet(conn, entry["name"])
            if existing is not None and not overwrite:
                skipped += 1
                continue
            add_snippet(
                conn, entry["name"], entry["content"], entry.get("tags", []), overwrite=True
            )
            imported += 1
    finally:
        conn.close()

    typer.secho(f"Imported {imported} snippet(s), skipped {skipped}", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
