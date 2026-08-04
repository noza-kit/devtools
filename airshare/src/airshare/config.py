from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PORT = 8000
DEFAULT_HOST = "0.0.0.0"


def _default_dir(name: str) -> Path:
    return Path.home() / "Documents" / "AirShare" / name


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    send_dir: Path
    receive_dir: Path
    passcode: str | None

    @property
    def runtime_dir(self) -> Path:
        return Path.home() / ".airshare"


def load_settings(
    *,
    host: str | None = None,
    port: int | None = None,
    send_dir: Path | None = None,
    receive_dir: Path | None = None,
    passcode: str | None = None,
) -> Settings:
    """Merge CLI overrides > environment variables > defaults, and ensure folders exist."""
    resolved_host = host or os.environ.get("AIRSHARE_HOST") or DEFAULT_HOST
    resolved_port = port or _int_env("AIRSHARE_PORT") or DEFAULT_PORT
    resolved_send = send_dir or _path_env("AIRSHARE_SEND_DIR") or _default_dir("send")
    resolved_receive = receive_dir or _path_env("AIRSHARE_RECEIVE_DIR") or _default_dir("received")
    resolved_passcode = passcode if passcode is not None else os.environ.get("AIRSHARE_PASSCODE") or None

    resolved_send = Path(resolved_send).expanduser().resolve()
    resolved_receive = Path(resolved_receive).expanduser().resolve()
    resolved_send.mkdir(parents=True, exist_ok=True)
    resolved_receive.mkdir(parents=True, exist_ok=True)

    return Settings(
        host=resolved_host,
        port=resolved_port,
        send_dir=resolved_send,
        receive_dir=resolved_receive,
        passcode=resolved_passcode,
    )


def _int_env(name: str) -> int | None:
    value = os.environ.get(name)
    return int(value) if value else None


def _path_env(name: str) -> Path | None:
    value = os.environ.get(name)
    return Path(value) if value else None
