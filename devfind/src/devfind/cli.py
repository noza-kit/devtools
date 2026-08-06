from __future__ import annotations

import concurrent.futures
import contextlib
import sys
from pathlib import Path
from typing import Optional

import typer

from devfind.config import load_settings
from devfind.fzf import run_fzf
from devfind.search import merge_results, run_fd, run_rg
from devfind.tools import MissingToolError, ensure_required_tools

if sys.platform == "win32":
    # The Windows console's codepage (e.g. cp932) can't encode the Japanese
    # status text this CLI prints; force UTF-8 regardless of the active codepage.
    for _stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(AttributeError, ValueError):
            _stream.reconfigure(encoding="utf-8", errors="replace")

app = typer.Typer(help="fd/fzf/ripgrep を組み合わせたファイル検索ラッパー")


@app.command()
def main(
    keyword: str = typer.Argument(..., help="検索キーワード(ファイル名・内容の両方に適用)"),
    config: Optional[Path] = typer.Option(
        None, "--config", help="設定ファイルのパス(デフォルト: ~/.devfind/config.yaml)"
    ),
) -> None:
    """ファイル名一致(fd)と内容一致(rg)を横断検索し、fzfで選んだパスを標準出力する。"""
    try:
        ensure_required_tools()
    except MissingToolError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    settings = load_settings(config)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        fd_future = executor.submit(run_fd, keyword, settings.target_dirs, settings.exclude)
        rg_future = executor.submit(run_rg, keyword, settings.target_dirs, settings.exclude)
        fd_paths = fd_future.result()
        rg_paths = rg_future.result()

    matches = merge_results(fd_paths, rg_paths)
    if not matches:
        typer.secho("一致するファイルが見つかりませんでした。", fg=typer.colors.YELLOW, err=True)
        raise typer.Exit(code=1)

    selected = run_fzf(matches)
    if selected is None:
        raise typer.Exit(code=130)

    typer.echo(selected)


if __name__ == "__main__":
    app()
