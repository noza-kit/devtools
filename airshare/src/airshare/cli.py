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

if sys.platform == "win32":
    # The Windows console's codepage (e.g. cp932) can't encode the QR ASCII
    # art or Japanese status text; force UTF-8 regardless of the active codepage.
    for _stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(AttributeError, ValueError):
            _stream.reconfigure(encoding="utf-8", errors="replace")

app = typer.Typer(help="AirDrop-like local file transfer server between iPhone and PC", add_completion=True)

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
