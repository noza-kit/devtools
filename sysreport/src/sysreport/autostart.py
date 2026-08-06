from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

DEFAULT_TASK_NAME = "SysReport"


class AutostartError(Exception):
    """Raised when `schtasks` fails to register or remove the autostart task."""


def resolve_sysreport_command() -> str:
    """Find the installed `sysreport` console script, falling back to `python -m`."""
    exe_path = Path(sys.executable).parent / "Scripts" / "sysreport.exe"
    if exe_path.exists():
        return f'"{exe_path}"'
    return f'"{sys.executable}" -m sysreport.cli'


def build_run_command(
    *,
    channels: Optional[list[str]] = None,
    config: Optional[Path] = None,
    highlight_warnings: bool = False,
) -> str:
    """Build the full `sysreport run ...` command line the scheduled task will execute."""
    parts = [resolve_sysreport_command(), "run"]
    if channels:
        parts.append(f"--channels {','.join(channels)}")
    if config:
        parts.append(f'--config "{config}"')
    if highlight_warnings:
        parts.append("--highlight-warnings")
    return " ".join(parts)


def register_autostart(
    *,
    task_name: str = DEFAULT_TASK_NAME,
    channels: Optional[list[str]] = None,
    config: Optional[Path] = None,
    highlight_warnings: bool = False,
) -> None:
    """Register a Task Scheduler task that runs `sysreport run` at user logon.

    Uses an `ONLOGON` trigger (not `ONSTART`) because desktop notifications
    need a logged-in user session to display in - a task running at boot
    under the SYSTEM account can't show one.
    """
    command = build_run_command(channels=channels, config=config, highlight_warnings=highlight_warnings)
    result = subprocess.run(
        [
            "schtasks",
            "/create",
            "/sc", "ONLOGON",
            "/tn", task_name,
            "/tr", command,
            "/rl", "LIMITED",
            "/f",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AutostartError(
            f"schtasks /create failed (exit {result.returncode}): {result.stderr.strip() or result.stdout.strip()}"
        )


def remove_autostart(*, task_name: str = DEFAULT_TASK_NAME) -> None:
    """Unregister the autostart task. Missing tasks are treated as already-removed."""
    result = subprocess.run(
        ["schtasks", "/delete", "/tn", task_name, "/f"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and "cannot find the file" not in result.stderr.lower():
        raise AutostartError(
            f"schtasks /delete failed (exit {result.returncode}): {result.stderr.strip() or result.stdout.strip()}"
        )
