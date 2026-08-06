from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Optional

import requests
import typer
import uvicorn

from airshare.config import load_settings
from airshare.network import get_local_ip, is_port_free
from airshare.qr import render_ascii
from airshare.runtime import RuntimeInfo, clear_runtime_info, generate_token, read_runtime_info, write_runtime_info
from airshare.server import create_app
from airshare.shortcut import create_desktop_shortcut
from airshare.watch_cleanup import find_stale_files, move_to_trash
from airshare.watch_config import load_watch_settings
from airshare.watch_daemon import run_watch_daemon
from airshare.watch_state import is_process_alive, read_recent_log_entries, read_watch_runtime_info

if sys.platform == "win32":
    # The Windows console's codepage (e.g. cp932) can't encode the QR ASCII
    # art or Japanese status text; force UTF-8 regardless of the active codepage.
    for _stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(AttributeError, ValueError):
            _stream.reconfigure(encoding="utf-8", errors="replace")

app = typer.Typer(help="AirDrop-like local file transfer server between iPhone and PC", add_completion=True)
watch_app = typer.Typer(help="Watch the Inbox and auto-organize/notify/clean up received files.")
app.add_typer(watch_app, name="watch")

HEALTH_TIMEOUT = 2.0


@app.command()
def start(
    port: Optional[int] = typer.Option(None, "--port", "-p", help="Port to listen on (default: 8000 or $AIRSHARE_PORT)"),
    send_dir: Optional[Path] = typer.Option(None, "--send-dir", help="Folder shared PC -> iPhone (default: ~/Documents/AirShare/send)"),
    receive_dir: Optional[Path] = typer.Option(None, "--receive-dir", help="Folder uploads land in, iPhone -> PC (default: ~/Documents/AirShare/received)"),
    passcode: Optional[str] = typer.Option(None, "--passcode", help="Passcode required to access the server (default: $AIRSHARE_PASSCODE, none)"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Do not open the QR code page in a browser"),
) -> None:
    """Start the local web server and print a QR code for iPhone to scan."""
    settings = load_settings(port=port, send_dir=send_dir, receive_dir=receive_dir, passcode=passcode)

    existing = read_runtime_info(settings)
    if existing is not None and _is_alive(existing):
        typer.secho(f"AirShare is already running on port {existing.port}. Run 'airshare stop' first.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if not is_port_free(settings.host, settings.port):
        typer.secho(
            f"ポート {settings.port} は他のアプリケーションが使用中です。"
            " '--port' で別の番号を指定するか、$AIRSHARE_PORT を変更してください。",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    token = generate_token()
    fastapi_app = create_app(settings, shutdown_token=token)

    ip = get_local_ip()
    url = f"http://{ip}:{settings.port}/"
    if settings.passcode:
        url = f"{url}?code={settings.passcode}"

    typer.echo(render_ascii(url))
    typer.secho(f"URL: {url}", fg=typer.colors.GREEN, bold=True)
    typer.echo(f"送信フォルダ (PC -> iPhone): {settings.send_dir}")
    typer.echo(f"受信フォルダ (iPhone -> PC): {settings.receive_dir}")
    typer.echo("Ctrl+C で停止、または別ターミナルから 'airshare stop'")

    config = uvicorn.Config(fastapi_app, host=settings.host, port=settings.port, log_level="warning")
    server = uvicorn.Server(config)
    fastapi_app.state.server = server

    write_runtime_info(settings, token)

    if not no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{settings.port}/qr")).start()

    try:
        server.run()
    finally:
        clear_runtime_info(settings)


@app.command()
def stop() -> None:
    """Stop a running AirShare server, gracefully via HTTP or by force as a fallback."""
    settings = load_settings()
    info = read_runtime_info(settings)
    if info is None:
        typer.secho("AirShare is not running (no runtime info found).", fg=typer.colors.YELLOW)
        raise typer.Exit(code=0)

    try:
        requests.post(
            f"http://127.0.0.1:{info.port}/api/shutdown",
            headers={"X-AirShare-Token": info.token},
            timeout=HEALTH_TIMEOUT,
        )
        typer.secho("AirShare stopped.", fg=typer.colors.GREEN)
    except requests.RequestException:
        typer.secho("Server did not respond; terminating the process directly.", fg=typer.colors.YELLOW)
        _force_kill(info.pid)

    clear_runtime_info(settings)


@app.command("setup-shortcut")
def setup_shortcut(
    port: Optional[int] = typer.Option(None, "--port", "-p", help="Port the shortcut should start the server on"),
    passcode: Optional[str] = typer.Option(None, "--passcode", help="Passcode the shortcut should set"),
) -> None:
    """Create a desktop .bat shortcut that starts AirShare and opens the QR page."""
    if sys.platform != "win32":
        typer.secho("setup-shortcut is only supported on Windows.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    settings = load_settings(port=port, passcode=passcode)
    shortcut_path = create_desktop_shortcut(settings)
    typer.secho(f"Created shortcut: {shortcut_path}", fg=typer.colors.GREEN)


@watch_app.command("start")
def watch_start(
    config: Optional[Path] = typer.Option(None, "--config", help="watch.yaml (default: ~/.airshare/watch.yaml)"),
    interval: float = typer.Option(1.0, "--interval", help="Seconds between checking for settled files"),
) -> None:
    """Watch the Inbox (default: airshare's own --receive-dir) and
    auto-route/hook/notify for newly-received files (Ctrl+C to stop)."""
    default_inbox = load_settings().receive_dir
    try:
        settings = load_watch_settings(config, default_inbox_dir=default_inbox)
    except FileNotFoundError as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho(f"Watching {settings.inbox_dir} (Ctrl+C で終了)", fg=typer.colors.GREEN, bold=True)
    run_watch_daemon(settings, poll_interval=interval)


@watch_app.command("status")
def watch_status(hours: float = typer.Option(24.0, "--hours", help="How far back to show activity")) -> None:
    """Show whether `watch start` is currently running, and recent (default: 24h) receive/processing activity."""
    info = read_watch_runtime_info()
    if info is not None and is_process_alive(info.pid):
        typer.secho(f"稼働中 (PID {info.pid}, 開始: {info.started_at})", fg=typer.colors.GREEN)
    else:
        typer.secho("停止中", fg=typer.colors.YELLOW)

    entries = read_recent_log_entries(within_hours=hours)
    if not entries:
        typer.echo(f"過去{hours:g}時間の受信履歴はありません。")
        return

    typer.echo(f"過去{hours:g}時間の受信履歴:")
    for entry in entries:
        typer.echo(f"  [{entry['timestamp']}] {entry['message']}")


@watch_app.command("clean")
def watch_clean(
    config: Optional[Path] = typer.Option(None, "--config"),
    force: bool = typer.Option(False, "--force", help="Skip the confirmation prompt"),
) -> None:
    """Manually run the same stale-file-to-recycle-bin cleanup `watch start` performs daily."""
    default_inbox = load_settings().receive_dir
    try:
        settings = load_watch_settings(config, default_inbox_dir=default_inbox)
    except FileNotFoundError as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if not settings.cleanup.enabled:
        typer.secho("cleanup は設定で無効化されています(cleanup.enabled: false)。", fg=typer.colors.YELLOW)
        raise typer.Exit(code=0)

    directories = [rule.destination for rule in settings.routing] + [settings.inbox_dir]
    stale = find_stale_files(directories, settings.cleanup.expire_days)
    if not stale:
        typer.echo("削除対象のファイルはありません。")
        return

    typer.echo(f"{len(stale)}件のファイルがゴミ箱へ移動されます:")
    for path in stale:
        typer.echo(f"  {path}")
    if not force and not typer.confirm("続行しますか?"):
        raise typer.Exit(code=0)

    for path in stale:
        move_to_trash(path)
    typer.secho(f"{len(stale)}件をゴミ箱へ移動しました。", fg=typer.colors.GREEN)


def _is_alive(info: RuntimeInfo) -> bool:
    try:
        response = requests.get(f"http://127.0.0.1:{info.port}/api/health", timeout=HEALTH_TIMEOUT)
        return response.status_code == 200
    except requests.RequestException:
        return False


def _force_kill(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, check=False)
    else:
        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, 15)


if __name__ == "__main__":
    app()
