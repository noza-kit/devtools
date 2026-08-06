from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Optional

import typer
from confload import ConfigError
from notify import notify

from sysreport.autostart import DEFAULT_TASK_NAME, AutostartError, register_autostart, remove_autostart
from sysreport.report import build_report, format_report, to_dict
from sysreport.thresholds import load_thresholds

app = typer.Typer(
    help="sysreport: PC startup health check (storage/battery/CPU/memory) delivered via notify()",
    add_completion=True,
)


@app.callback()
def main() -> None:
    """sysreport: PC startup health check (storage/battery/CPU/memory) delivered via notify()."""


@app.command()
def run(
    channels: str = typer.Option(
        "desktop", "--channels", help="Comma-separated notify channels to send to (desktop, slack, discord, line)"
    ),
    config: Optional[Path] = typer.Option(None, "--config", help="YAML/JSON file with threshold overrides"),
    storage_min_percent: Optional[float] = typer.Option(
        None, "--storage-min-percent", help="Override: warn when a drive's free space drops to/below this percent"
    ),
    battery_min_percent: Optional[float] = typer.Option(
        None, "--battery-min-percent", help="Override: warn when battery drops to/below this percent while unplugged"
    ),
    cpu_max_percent: Optional[float] = typer.Option(
        None, "--cpu-max-percent", help="Override: warn when CPU usage rises to/above this percent"
    ),
    memory_max_percent: Optional[float] = typer.Option(
        None, "--memory-max-percent", help="Override: warn when memory usage rises to/above this percent"
    ),
    highlight_warnings: bool = typer.Option(
        False, "--highlight-warnings", "-w", help="Mark items that crossed their threshold with a warning mark"
    ),
    json_output: bool = typer.Option(False, "--json", help="Print the report as JSON instead of the emoji summary"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the report but don't send a notification"),
    cpu_interval: float = typer.Option(
        0.5, "--cpu-interval", help="Seconds to sample CPU usage over (higher = more accurate)"
    ),
) -> None:
    """Check storage/battery/CPU/memory and send the result through notify()."""
    try:
        thresholds = load_thresholds(config)
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)

    cli_overrides = {
        "storage_min_free_percent": storage_min_percent,
        "battery_min_percent": battery_min_percent,
        "cpu_max_percent": cpu_max_percent,
        "memory_max_percent": memory_max_percent,
    }
    thresholds = replace(thresholds, **{k: v for k, v in cli_overrides.items() if v is not None})

    report = build_report(cpu_interval=cpu_interval)
    text = format_report(report, thresholds, highlight_warnings=highlight_warnings)

    if json_output:
        typer.echo(json.dumps(to_dict(report, thresholds), ensure_ascii=False, indent=2))
    else:
        typer.echo(text)

    if dry_run:
        return

    channel_list = [c.strip() for c in channels.split(",") if c.strip()]
    results = notify(text, channel_list)
    failed = [channel for channel, result in results.items() if not result.ok]
    if failed:
        typer.secho(f"Warning: notification failed on: {', '.join(failed)}", fg=typer.colors.YELLOW)


@app.command("setup-autostart")
def setup_autostart(
    task_name: str = typer.Option(DEFAULT_TASK_NAME, "--task-name", help="Scheduled Task name"),
    channels: str = typer.Option(
        "desktop", "--channels", help="Comma-separated notify channels the scheduled run should use"
    ),
    config: Optional[Path] = typer.Option(
        None, "--config", help="Threshold config file the scheduled run should use"
    ),
    highlight_warnings: bool = typer.Option(
        False, "--highlight-warnings", help="Have the scheduled run mark threshold warnings"
    ),
    remove: bool = typer.Option(False, "--remove", help="Remove the autostart task instead of registering it"),
) -> None:
    """Register (or --remove) a Task Scheduler task that runs `sysreport run` at logon."""
    try:
        if remove:
            remove_autostart(task_name=task_name)
            typer.secho(f"Removed autostart task '{task_name}'.", fg=typer.colors.GREEN)
            return

        channel_list = [c.strip() for c in channels.split(",") if c.strip()]
        register_autostart(
            task_name=task_name, channels=channel_list, config=config, highlight_warnings=highlight_warnings
        )
        typer.secho(f"Registered autostart task '{task_name}' (runs at logon).", fg=typer.colors.GREEN)
    except AutostartError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
