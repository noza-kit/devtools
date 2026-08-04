from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import List, Optional

import typer

from devtoolbox.common.paths import experiments_db_path
from devtoolbox.explog.db import Run, get_connection, get_run, list_runs

app = typer.Typer(help="Generic experiment run logger", add_completion=True)


def _truncate(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"


def _format_kv(d: dict, width: int = 40) -> str:
    return _truncate(", ".join(f"{k}={v}" for k, v in d.items()), width)


def _format_table(runs: list[Run]) -> str:
    headers = ["ID", "Timestamp", "Tags", "Params", "Results"]
    rows = [
        [
            str(r.id),
            r.timestamp,
            ", ".join(r.tags),
            _format_kv(r.params),
            _format_kv(r.results),
        ]
        for r in runs
    ]
    widths = [
        max(len(headers[i]), *(len(row[i]) for row in rows)) for i in range(len(headers))
    ]

    def _format_row(cells: list[str]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells))

    lines = [_format_row(headers), "  ".join("-" * w for w in widths)]
    lines.extend(_format_row(row) for row in rows)
    return "\n".join(lines)


@app.command(name="list")
def list_cmd(
    limit: int = typer.Option(20, "--limit", "-n", help="Show at most N most recent runs"),
    tag: List[str] = typer.Option(
        [], "--tag", "-t", help="Filter by tag (repeatable; a run must have all given tags)"
    ),
) -> None:
    """List past experiment runs as a table (most recent first)."""
    conn = get_connection(experiments_db_path())
    try:
        runs = list_runs(conn, tags=tag or None, limit=limit)
    finally:
        conn.close()

    if not runs:
        typer.echo("No runs found.")
        return

    typer.echo(_format_table(runs))


@app.command()
def show(run_id: int = typer.Argument(..., help="Run id")) -> None:
    """Show full details (all params and results) for one run."""
    conn = get_connection(experiments_db_path())
    try:
        run = get_run(conn, run_id)
    finally:
        conn.close()

    if run is None:
        typer.secho(f"Run #{run_id} not found", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.echo(f"Run #{run.id}")
    typer.echo(f"Timestamp: {run.timestamp}")
    typer.echo(f"Tags: {', '.join(run.tags) if run.tags else '(none)'}")
    typer.echo("Params:")
    typer.echo(json.dumps(run.params, ensure_ascii=False, indent=2))
    typer.echo("Results:")
    typer.echo(json.dumps(run.results, ensure_ascii=False, indent=2))


@app.command()
def export(
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output file (default: print to stdout)"
    ),
    format: str = typer.Option("csv", "--format", "-f", help="Export format (csv)"),
    tag: List[str] = typer.Option(
        [], "--tag", "-t", help="Filter by tag (repeatable; a run must have all given tags)"
    ),
) -> None:
    """Export run history to CSV."""
    if format != "csv":
        typer.secho(f"Unsupported format: {format!r} (only 'csv' is supported)", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    conn = get_connection(experiments_db_path())
    try:
        runs = list_runs(conn, tags=tag or None)
    finally:
        conn.close()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "timestamp", "tags", "params", "results"])
    for r in runs:
        writer.writerow(
            [
                r.id,
                r.timestamp,
                ",".join(r.tags),
                json.dumps(r.params, ensure_ascii=False),
                json.dumps(r.results, ensure_ascii=False),
            ]
        )
    text = buffer.getvalue()

    if output is not None:
        output.write_text(text, encoding="utf-8", newline="")
        typer.secho(f"Exported {len(runs)} run(s) to {output}", fg=typer.colors.GREEN)
    else:
        typer.echo(text, nl=False)


if __name__ == "__main__":
    app()
