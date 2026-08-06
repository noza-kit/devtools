from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from slidecraft.builder import build_presentation
from slidecraft.parser import SlideParseError, parse_html
from slidecraft.prompt import get_prompt

app = typer.Typer(help="Convert LLM-generated structured HTML into an editable PPTX.")
console = Console()
err_console = Console(stderr=True)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    get_prompt_flag: bool = typer.Option(False, "--get-prompt", help="Print the LLM system prompt for slidecraft's expected HTML format, and exit."),
) -> None:
    if get_prompt_flag:
        print(get_prompt())
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit()


@app.command()
def generate(
    html: Path,
    output: Path = typer.Option(..., "-o", "--output"),
    template: Optional[Path] = typer.Option(None, "--template", help="An existing .pptx to use as the base (fonts/background/placeholder layout). Omit to use a minimal built-in default."),
) -> None:
    """Convert HTML into a PPTX."""
    if not html.exists():
        err_console.print(f"[red]エラー: HTMLファイルが見つかりません: {html}[/red]")
        raise typer.Exit(code=1)
    if template is not None and not template.exists():
        err_console.print(f"[red]エラー: テンプレートファイルが見つかりません: {template}[/red]")
        raise typer.Exit(code=1)

    try:
        slides = parse_html(html)
    except SlideParseError as e:
        err_console.print(f"[red]エラー: {e}[/red]")
        raise typer.Exit(code=1)

    prs = build_presentation(slides, template_path=template)
    output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(output)

    console.print(f"[green]{len(slides)}枚のスライドを生成しました[/green] -> {output}")
