from __future__ import annotations

import sys
from pathlib import Path

from airshare.config import Settings

SHORTCUT_NAME = "AirShare 起動.bat"


def desktop_dir() -> Path:
    return Path.home() / "Desktop"


def create_desktop_shortcut(settings: Settings) -> Path:
    """Write a double-click-able .bat on the Desktop that starts `airshare start`."""
    desktop = desktop_dir()
    desktop.mkdir(parents=True, exist_ok=True)
    target = desktop / SHORTCUT_NAME

    lines = ["@echo off", "chcp 65001 >nul", f"set AIRSHARE_PORT={settings.port}"]
    if settings.passcode:
        lines.append(f"set AIRSHARE_PASSCODE={settings.passcode}")
    lines.append(f"{_airshare_command()} start")
    lines.append("pause")

    target.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    return target


def _airshare_command() -> str:
    exe_path = Path(sys.executable).parent / "Scripts" / "airshare.exe"
    if exe_path.exists():
        return f'"{exe_path}"'
    return f'"{sys.executable}" -m airshare.cli'
