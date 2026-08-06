from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

DEFAULT_TASK_NAME = "KanbancliRemind"
DEFAULT_TIME = "09:00"


class AutostartError(Exception):
    """Raised when `schtasks` fails to register or remove the reminder task."""


def resolve_kanbancli_command() -> str:
    exe_path = Path(sys.executable).parent / "Scripts" / "kanbancli.exe"
    if exe_path.exists():
        return f'"{exe_path}"'
    return f'"{sys.executable}" -m kanbancli.cli'


def build_run_command(
    *,
    within_days: int = 3,
    channels: Optional[list[str]] = None,
    file: Optional[Path] = None,
) -> str:
    parts = [resolve_kanbancli_command(), "remind", "--within-days", str(within_days)]
    if channels:
        parts.append(f"--channels {','.join(channels)}")
    if file:
        parts.append(f'--file "{file}"')
    return " ".join(parts)


def register_autostart(
    *,
    task_name: str = DEFAULT_TASK_NAME,
    start_time: str = DEFAULT_TIME,
    within_days: int = 3,
    channels: Optional[list[str]] = None,
    file: Optional[Path] = None,
) -> None:
    """Registers a daily Task Scheduler task (not just at-logon, since a
    due-date reminder should fire on a schedule even across a session
    that's stayed logged in for days) that runs `kanbancli remind`.
    `/rl LIMITED` runs it without admin rights; desktop notifications
    need an active logon session, so this is still a per-user task, not
    a SYSTEM-account one."""
    command = build_run_command(within_days=within_days, channels=channels, file=file)
    result = subprocess.run(
        [
            "schtasks",
            "/create",
            "/sc", "DAILY",
            "/st", start_time,
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
    result = subprocess.run(
        ["schtasks", "/delete", "/tn", task_name, "/f"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and "cannot find the file" not in result.stderr.lower():
        raise AutostartError(
            f"schtasks /delete failed (exit {result.returncode}): {result.stderr.strip() or result.stdout.strip()}"
        )
