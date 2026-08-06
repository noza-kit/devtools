from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import typer

from mailwatch.auth import AuthError, load_credentials
from mailwatch.paths import default_credentials_path, default_db_path, default_token_path
from mailwatch.poller import run_forever
from mailwatch.rules import RuleConfigError, load_rules_config
from mailwatch.store import SeenStore

app = typer.Typer(
    help="Poll Gmail for messages matching rules in a YAML config, and notify via Slack/Discord/etc.",
    add_completion=True,
)


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


@app.command()
def auth(
    credentials: Optional[Path] = typer.Option(
        None, "--credentials", help="OAuth client secrets JSON (default: ~/.mailwatch/credentials.json)"
    ),
    token: Optional[Path] = typer.Option(
        None, "--token", help="Where to store the OAuth token (default: ~/.mailwatch/token.json)"
    ),
    force: bool = typer.Option(False, "--force", help="Discard any existing token and re-run the consent flow"),
) -> None:
    """Run the Gmail OAuth2 consent flow (opens a browser) and save the token."""
    credentials = credentials or default_credentials_path()
    token = token or default_token_path()

    if force and token.exists():
        token.unlink()

    try:
        load_credentials(credentials, token, interactive=True)
    except AuthError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho(f"Authenticated. Token saved to {token}", fg=typer.colors.GREEN)


@app.command()
def start(
    config: Path = typer.Option(..., "--config", "-c", help="YAML file defining watch rules"),
    interval: Optional[int] = typer.Option(
        None, "--interval", help="Poll interval in seconds (overrides poll_interval_seconds in config)"
    ),
    credentials: Optional[Path] = typer.Option(
        None, "--credentials", help="OAuth client secrets JSON (default: ~/.mailwatch/credentials.json)"
    ),
    token: Optional[Path] = typer.Option(
        None, "--token", help="OAuth token storage path (default: ~/.mailwatch/token.json)"
    ),
    db: Optional[Path] = typer.Option(
        None, "--db", help="SQLite DB for processed message IDs (default: ~/.mailwatch/seen.db)"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Debug logging"),
) -> None:
    """Start polling Gmail. On first run (no saved token), opens a browser for
    the OAuth consent flow; subsequent runs refresh the token silently."""
    _configure_logging(verbose)

    credentials = credentials or default_credentials_path()
    token = token or default_token_path()
    db = db or default_db_path()

    if not config.exists():
        typer.secho(f"Config file not found: {config}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    try:
        watch_config = load_rules_config(config)
    except RuleConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)

    interval_seconds = interval if interval is not None else watch_config.poll_interval_seconds

    with SeenStore(db) as store:
        try:
            run_forever(
                credentials_path=credentials,
                token_path=token,
                config=watch_config,
                store=store,
                interval_seconds=interval_seconds,
            )
        except AuthError as exc:
            typer.secho(str(exc), fg=typer.colors.RED)
            raise typer.Exit(code=1)
        except KeyboardInterrupt:
            typer.echo("Stopped.")


if __name__ == "__main__":
    app()
