from __future__ import annotations

from pathlib import Path

import typer

from wikigen.core import SITE_TITLE, build_site
from wikigen.server import serve_directory

app = typer.Typer(
    help="Static searchable wiki site generator from a folder of Markdown notes",
    add_completion=True,
)


@app.command()
def build(
    source: Path = typer.Argument(..., help="Folder containing Markdown (.md) notes, searched recursively"),
    output: Path = typer.Option(Path("site"), "--output", "-o", help="Output folder for the generated static site"),
    title: str = typer.Option(SITE_TITLE, "--title", help="Site title shown in the sidebar and page titles"),
) -> None:
    """Build a static, searchable HTML wiki from a folder of Markdown notes."""
    try:
        pages = build_site(source, output, site_title=title)
    except (FileNotFoundError, ValueError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho(f"Built {len(pages)} page(s) -> {output}", fg=typer.colors.GREEN)


@app.command()
def serve(
    directory: Path = typer.Argument(Path("site"), help="Built site folder to serve (default: ./site)"),
    port: int = typer.Option(8000, "--port", "-p", help="Local port to listen on"),
) -> None:
    """Serve a previously built site folder locally for preview."""
    if not directory.is_dir():
        typer.secho(f"Folder not found: {directory} (run 'wikigen build' first)", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho(f"Serving {directory} at http://127.0.0.1:{port}/ (Ctrl+C to stop)", fg=typer.colors.GREEN)
    serve_directory(directory, port)


if __name__ == "__main__":
    app()
