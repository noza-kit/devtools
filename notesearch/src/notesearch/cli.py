from __future__ import annotations

from pathlib import Path
from typing import Optional

import click
import typer
from rich.console import Console
from typer.core import TyperGroup

from notesearch import config as config_mod
from notesearch import gemini as gemini_mod
from notesearch import search as search_mod
from notesearch import sync as sync_mod
from notesearch import watcher as watcher_mod
from notesearch.embeddings import SentenceTransformerEmbedder
from notesearch.ragprompt import copy_to_clipboard, format_rag_prompt
from notesearch.vectordb import VectorStore

DEFAULT_COMMAND = "search"


class DefaultCommandGroup(TyperGroup):
    """Makes `notesearch "query" [options]` work without a `search`
    keyword (per the spec's own CLI examples), while `notesearch
    daemon start` / `notesearch clean` / `notesearch sync` still reach
    those as ordinary subcommands: a first token that isn't a
    registered command name (and isn't an option starting with "-") is
    treated as the start of a `search` invocation instead. This means
    a query that happens to be exactly "clean", "sync", or "daemon"
    will be swallowed by the matching subcommand instead of searched
    for -- a real, if narrow, ambiguity inherent to mixing a bare-
    positional default action with named subcommands; see README's
    "Known limitations"."""

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        if args and not args[0].startswith("-") and args[0] not in self.commands:
            args = [DEFAULT_COMMAND, *args]
        return super().parse_args(ctx, args)


app = typer.Typer(
    cls=DefaultCommandGroup,
    no_args_is_help=True,
    help="Local semantic + keyword hybrid search over a notes directory.",
)
daemon_app = typer.Typer(help="Background auto-sync mode (alternative to the default per-search JIT sync).")
app.add_typer(daemon_app, name="daemon")

console = Console()
err_console = Console(stderr=True)


def _fail(message: str) -> None:
    err_console.print(f"[red]エラー: {message}[/red]")
    raise typer.Exit(code=1)


def _load_settings_or_fail(config: Optional[Path]) -> config_mod.Settings:
    try:
        return config_mod.load_settings(config)
    except FileNotFoundError as e:
        _fail(str(e))


def _open_store(settings: config_mod.Settings) -> VectorStore:
    return VectorStore(settings.db_dir, SentenceTransformerEmbedder())


@app.command(name=DEFAULT_COMMAND)
def search(
    query: str,
    dir: Optional[str] = typer.Option(None, "--dir", help="ディレクトリ名で絞り込み"),
    days: Optional[int] = typer.Option(None, "--days", help="過去N日以内に更新されたファイルのみ"),
    top: int = typer.Option(5, "--top", help="上位何件を対象にするか"),
    copy: bool = typer.Option(False, "--copy", help="検索結果をLLM用プロンプトとしてクリップボードにコピー(TUIは開かない)"),
    ask: bool = typer.Option(False, "--ask", help="検索結果を元にGemini APIへ質問し、回答を表示する(TUIは開かない)"),
    config: Optional[Path] = typer.Option(None, "--config"),
) -> None:
    """`notesearch "query"` で意味検索(起動時に自動でJIT Syncが走る)。"""
    settings = _load_settings_or_fail(config)

    store = _open_store(settings)
    results, report = search_mod.search(query, store, settings, top_k=top, directory=dir, since_days=days)
    if report.changed:
        console.print(f"[dim](sync: +{report.added} added, {report.updated} updated)[/dim]")

    if copy:
        prompt = format_rag_prompt(results)
        copy_to_clipboard(prompt)
        console.print(f"[green]{len(results)}件の結果をRAGプロンプトとしてクリップボードにコピーしました[/green]")
        return

    if ask:
        if not results:
            console.print("該当する結果がありません。")
            return
        prompt = format_rag_prompt(results, question=query)
        try:
            answer = gemini_mod.ask(prompt, api_key=settings.gemini_api_key)
        except gemini_mod.GeminiError as e:
            _fail(str(e))
        console.print(answer)
        return

    from notesearch.tui import run_search_tui

    run_search_tui(results, settings.editor_command, console=console)


@app.command()
def sync(config: Optional[Path] = typer.Option(None, "--config")) -> None:
    """Manually run JIT sync once, without searching."""
    settings = _load_settings_or_fail(config)
    store = _open_store(settings)
    report = sync_mod.sync_index(store, settings)
    console.print(f"[green]同期しました[/green]: +{report.added} 追加, {report.updated} 更新, {report.unchanged} 変更なし")


@app.command()
def clean(config: Optional[Path] = typer.Option(None, "--config")) -> None:
    """Purge index entries for files that no longer exist on disk."""
    settings = _load_settings_or_fail(config)
    store = _open_store(settings)
    report = sync_mod.clean_index(store)
    console.print(f"[green]{report.removed}件のゴーストデータを削除しました[/green]")


@daemon_app.command("start")
def daemon_start(
    config: Optional[Path] = typer.Option(None, "--config"),
    interval: float = typer.Option(5.0, "--interval", help="ファイル変更を検知してから再同期までの最小間隔(秒)"),
) -> None:
    """Watch target_dirs and auto-sync in the background (Ctrl+C to stop)."""
    settings = _load_settings_or_fail(config)
    store = _open_store(settings)

    def on_change() -> None:
        report = sync_mod.sync_index(store, settings)
        if report.changed:
            console.print(f"[dim]sync: +{report.added} added, {report.updated} updated[/dim]")

    console.print(f"[green]デーモンを起動しました[/green] ({', '.join(str(d) for d in settings.target_dirs)}). Ctrl+C で終了")
    try:
        watcher_mod.run_daemon(settings.target_dirs, on_change, poll_interval=interval)
    except ValueError as e:
        _fail(str(e))
