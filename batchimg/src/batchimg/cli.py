from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from batchimg.core import Options, execute, plan
from batchimg.resize import InvalidSizeError, parse_size

app = typer.Typer(
    help="Batch resize/rename/trim images and videos, with a preview-before-run workflow",
    add_completion=True,
)


@app.command()
def main(
    source_dir: Path = typer.Argument(..., help="Directory containing images/videos to process"),
    resize: Optional[str] = typer.Option(None, "--resize", help="Target size WIDTHxHEIGHT, e.g. 800x600"),
    keep_aspect: bool = typer.Option(
        True, "--keep-aspect/--no-keep-aspect",
        help="Preserve aspect ratio, fitting within --resize (default) instead of stretching to it exactly",
    ),
    rename: Optional[str] = typer.Option(
        None, "--rename",
        help='Output filename template, e.g. "img_{n}" or "{date}_{n}". '
        "Placeholders: {n} sequence number, {date} file date, {stem} original name, {ext} original extension",
    ),
    start: int = typer.Option(1, "--start", help="Starting number for {n}"),
    digits: int = typer.Option(4, "--digits", help="Zero-padded width for {n}"),
    date_format: str = typer.Option("%Y%m%d", "--date-format", help="strftime pattern for {date}"),
    trim_start: Optional[float] = typer.Option(None, "--trim-start", help="Trim video start time in seconds"),
    trim_end: Optional[float] = typer.Option(None, "--trim-end", help="Trim video end time in seconds"),
    pattern: Optional[str] = typer.Option(
        None, "--pattern", "-p",
        help="Glob pattern(s), comma-separated (default: common image/video extensions)",
    ),
    recursive: bool = typer.Option(False, "--recursive/--no-recursive", help="Recurse into subdirectories"),
    output_dir: Optional[Path] = typer.Option(
        None, "--output-dir", "-o", help="Output directory (default: SOURCE_DIR/batchimg_out)"
    ),
    in_place: bool = typer.Option(
        False, "--in-place",
        help="Overwrite files in SOURCE_DIR instead of writing to a separate output directory (destructive)",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show the preview only; never writes files"),
) -> None:
    """Preview, then batch-process images and videos in SOURCE_DIR."""
    if not source_dir.is_dir():
        typer.secho(f"Not a directory: {source_dir}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if in_place and output_dir is not None:
        typer.secho("Cannot combine --in-place with --output-dir", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    try:
        target_size = parse_size(resize) if resize else None
    except InvalidSizeError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if trim_start is not None and trim_end is not None and trim_end <= trim_start:
        typer.secho("--trim-end must be greater than --trim-start", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    patterns = [p.strip() for p in pattern.split(",")] if pattern else None
    resolved_output = source_dir if in_place else (output_dir or source_dir / "batchimg_out")

    options = Options(
        resize=target_size,
        keep_aspect=keep_aspect,
        rename_template=rename,
        start=start,
        digits=digits,
        date_format=date_format,
        trim_start=trim_start,
        trim_end=trim_end,
    )

    items = plan(source_dir, resolved_output, options, patterns=patterns, recursive=recursive)
    if not items:
        typer.echo("No matching images or videos found.")
        return

    typer.echo(f"{len(items)} file(s) will be processed -> {resolved_output}")
    for item in items:
        rel_src = item.source.relative_to(source_dir)
        try:
            rel_dst = item.destination.relative_to(resolved_output)
        except ValueError:
            rel_dst = item.destination
        typer.echo(f"  [{item.kind}] {rel_src} -> {rel_dst}")

    if dry_run:
        typer.echo("(dry run, no files written)")
        return

    if in_place:
        typer.secho("--in-place will overwrite original files.", fg=typer.colors.YELLOW)

    if not yes and not typer.confirm("Proceed?"):
        typer.echo("Aborted.")
        raise typer.Exit(code=1)

    processed, errors = execute(items, options)
    for msg in errors:
        typer.secho(f"error: {msg}", fg=typer.colors.RED)

    typer.secho(f"Processed {processed}/{len(items)} file(s) into {resolved_output}", fg=typer.colors.GREEN)
    if errors:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
