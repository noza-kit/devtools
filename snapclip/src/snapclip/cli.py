from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from snapclip import config as config_mod
from snapclip import webcapture
from snapclip.daemon import DEFAULT_HOTKEYS, Daemon
from snapclip.history import HistoryStore

app = typer.Typer(help="Windows screenshot + clipboard extension: stack capture with auto-markup, scroll stitching, full-page web capture, and FIFO clipboard history.")
daemon_app = typer.Typer(help="Run/manage the background hotkey daemon.")
app.add_typer(daemon_app, name="daemon")

console = Console()
err_console = Console(stderr=True)


def _fail(message: str) -> None:
    err_console.print(f"[red]エラー: {message}[/red]")
    raise typer.Exit(code=1)


@daemon_app.command("start")
def daemon_start(
    mode: Optional[str] = typer.Option(None, "--mode", help="markdown/latex; overrides the saved config for this run"),
    img_dir: Optional[Path] = typer.Option(None, "--img-dir"),
    paste_mode: str = typer.Option("one", "--paste-mode", help='"one" (pop one item per Alt+Shift+V press) or "all" (pop and paste everything at once)'),
    snap_key: str = typer.Option(DEFAULT_HOTKEYS["snap"], "--snap-key"),
    paste_key: str = typer.Option(DEFAULT_HOTKEYS["paste"], "--paste-key"),
    scroll_key: str = typer.Option(DEFAULT_HOTKEYS["scroll"], "--scroll-key"),
) -> None:
    """Start the background daemon (Ctrl+C to stop). Registers global
    hotkeys: Alt+Shift+S (stack screenshot), Alt+Shift+V (FIFO paste),
    Alt+Shift+C held (scroll capture)."""
    settings = config_mod.with_overrides(config_mod.load_settings(), mode=mode, img_dir=img_dir)
    try:
        with HistoryStore() as history:
            daemon = Daemon(
                settings,
                history=history,
                hotkeys={"snap": snap_key, "paste": paste_key, "scroll": scroll_key},
                paste_mode=paste_mode,
            )
            console.print(
                f"[green]snapclip daemon起動[/green] (mode={settings.mode}, img_dir={settings.img_dir})\n"
                f"  {snap_key} : スタックスクリーンショット\n"
                f"  {paste_key} : FIFOペースト\n"
                f"  {scroll_key} (押しっぱなし) : スクロールキャプチャ\n"
                "Ctrl+C で終了"
            )
            daemon.run_forever()
    except ValueError as e:
        _fail(str(e))


@app.command()
def web(
    url: str,
    output: Path = typer.Option(..., "-o", "--output"),
    viewport_width: int = typer.Option(1280, "--viewport-width"),
) -> None:
    """Full-page screenshot of URL via a headless browser (needs the
    'web' extra: pip install -e ".[web]", then `playwright install
    chromium` once)."""
    try:
        webcapture.capture_full_page(url, output, viewport_width)
    except ImportError as e:
        _fail(str(e))
    console.print(f"[green]保存しました[/green] -> {output}")


@app.command()
def history(limit: int = typer.Option(200, "--limit")) -> None:
    """Interactively search clipboard history (fzf-style); selecting an
    entry re-sets it as the current clipboard content."""
    from snapclip.clipboard import Win32ClipboardBackend
    from snapclip.tui import run_history_tui

    with HistoryStore() as store:
        entries = store.all(limit=limit)
        if not entries:
            console.print("履歴がありません。")
            return

        backend = Win32ClipboardBackend()

        def on_select(entry):
            if entry.kind == "text":
                backend.set_text(entry.content)
            else:
                from PIL import Image

                backend.set_image(Image.open(entry.content))

        picked = run_history_tui(entries, on_select, console=console)
        if picked:
            console.print(f"[green]クリップボードに再設定しました[/green]: {picked.preview()}")


@app.command()
def config(
    mode: Optional[str] = typer.Option(None, "--mode", help="markdown/latex"),
    img_dir: Optional[Path] = typer.Option(None, "--img-dir"),
    show: bool = typer.Option(False, "--show", help="Print the current config instead of changing it"),
) -> None:
    """View or update the saved config (~/.snapclip/config.yaml)."""
    current = config_mod.load_settings()

    if show or (mode is None and img_dir is None):
        table = Table("key", "value")
        table.add_row("mode", current.mode)
        table.add_row("img_dir", str(current.img_dir))
        console.print(table)
        return

    try:
        updated = config_mod.with_overrides(current, mode=mode, img_dir=img_dir)
    except ValueError as e:
        _fail(str(e))
    path = config_mod.save_settings(updated)
    console.print(f"[green]設定を保存しました[/green] -> {path}")
