from __future__ import annotations

import logging
import sys
from pathlib import Path

import typer

for _stream in (sys.stdout, sys.stderr):
    # On Windows, stdout/stderr often default to the system codepage rather
    # than UTF-8, which mangles non-ASCII text (Japanese instructions/status)
    # when printed to a UTF-8 terminal.
    if hasattr(_stream, "reconfigure") and (_stream.encoding or "").lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8")

from claude_bridge.config import ConfigError, load_secrets, load_settings
from claude_bridge.history_db import HistoryDB
from claude_bridge.runtime_state import clear_runtime_state, is_process_alive, read_runtime_state

app = typer.Typer(help="DiscordからClaude Codeを遠隔操作する常駐Bot", add_completion=True)

DEFAULT_CONFIG_PATH = Path("bridge.yaml")
DEFAULT_DB_PATH = Path.home() / ".claude-bridge" / "history.db"


@app.command()
def start(
    config: Path = typer.Option(DEFAULT_CONFIG_PATH, "--config", help="プロジェクトホワイトリスト等を定義するYAML"),
    db: Path = typer.Option(DEFAULT_DB_PATH, "--db", help="履歴/セッションSQLiteファイル"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="デバッグログを有効化"),
) -> None:
    """常駐Botを起動する(Ctrl+Cで停止)。"""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        settings = load_settings(config)
        secrets = load_secrets()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)

    existing = read_runtime_state()
    if existing is not None and is_process_alive(existing.pid):
        typer.secho(f"claude-bridge は既に起動しています (PID {existing.pid})。", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    from claude_bridge.discord_bot import BridgeClient

    typer.secho(
        f"claude-bridge を起動します(プロジェクト: {', '.join(p.alias for p in settings.projects)})",
        fg=typer.colors.GREEN,
    )

    with HistoryDB(db) as history_db:
        client = BridgeClient(settings, secrets, history_db)
        try:
            client.run(secrets.bot_token)
        except KeyboardInterrupt:
            pass
        finally:
            clear_runtime_state()


@app.command()
def status() -> None:
    """稼働状況(実行中/待機中/一時停止中/キュー件数)を表示する。"""
    info = read_runtime_state()
    if info is None or not is_process_alive(info.pid):
        typer.secho("停止中(プロセスなし)", fg=typer.colors.YELLOW)
        raise typer.Exit(code=0)

    typer.secho(f"起動中 (PID {info.pid}, 開始: {info.started_at})", fg=typer.colors.GREEN)
    if info.paused:
        typer.secho("状態: 一時停止中(Discordで `起動` と送信すると再開)", fg=typer.colors.YELLOW)
    else:
        typer.echo(f"実行中: {info.current}" if info.current else "待機中")
    typer.echo(f"キュー: {info.queue_length}件")


@app.command()
def ping() -> None:
    """Discordチャンネルへヘルスチェックメッセージを送信し、接続設定を検証する。"""
    from claude_bridge.discord_rest import DiscordRestError, send_ping

    try:
        secrets = load_secrets()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)

    try:
        send_ping(secrets)
    except DiscordRestError as exc:
        typer.secho(f"ping に失敗しました: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho("ping を送信しました。", fg=typer.colors.GREEN)


@app.command()
def usage(
    db: Path = typer.Option(DEFAULT_DB_PATH, "--db", help="履歴/セッションSQLiteファイル"),
) -> None:
    """Claude Code の使用量(実行回数・概算コスト)を表示する。"""
    with HistoryDB(db) as history_db:
        all_time = history_db.usage_summary()
        recent = history_db.usage_summary(since_days=7)
        by_project = history_db.usage_by_project()

    typer.echo(f"全期間: {all_time.run_count}回 / ${all_time.total_cost_usd:.4f}")
    typer.echo(f"直近7日間: {recent.run_count}回 / ${recent.total_cost_usd:.4f}")
    if by_project:
        typer.echo("")
        typer.echo("プロジェクト別(全期間):")
        for p in by_project:
            typer.echo(f"  {p.project_alias}: {p.run_count}回 / ${p.total_cost_usd:.4f}")


if __name__ == "__main__":
    app()
