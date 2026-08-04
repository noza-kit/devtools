from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from devtoolbox.doctor.collectors import collect_report, format_human

app = typer.Typer(
    help="Report system/environment info, handy for reproducibility notes",
    add_completion=True,
)


@app.command()
def main(
    json_output: bool = typer.Option(
        False, "--json", help="Output as JSON instead of human-readable text"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Write the report to a file instead of stdout"
    ),
    pip: bool = typer.Option(False, "--pip", help="Include `pip freeze` output"),
    gpu: bool = typer.Option(
        True, "--gpu/--no-gpu", help="Attempt GPU detection (queries nvidia-smi/OS tools)"
    ),
) -> None:
    """Print a system/environment report, handy to paste into experiment notes."""
    report = collect_report(include_pip=pip, include_gpu=gpu)
    text = json.dumps(report, indent=2, ensure_ascii=False) if json_output else format_human(report)

    if output is not None:
        output.write_text(text, encoding="utf-8")
        typer.secho(f"Report written to {output}", fg=typer.colors.GREEN)
    else:
        typer.echo(text)


if __name__ == "__main__":
    app()
