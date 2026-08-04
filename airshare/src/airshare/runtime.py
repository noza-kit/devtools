from __future__ import annotations

import json
import os
import secrets
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from airshare.config import Settings

RUNTIME_FILENAME = "run.json"


@dataclass(frozen=True)
class RuntimeInfo:
    pid: int
    host: str
    port: int
    token: str


def generate_token() -> str:
    return secrets.token_urlsafe(24)


def _runtime_path(settings: Settings) -> Path:
    settings.runtime_dir.mkdir(parents=True, exist_ok=True)
    return settings.runtime_dir / RUNTIME_FILENAME


def write_runtime_info(settings: Settings, token: str) -> RuntimeInfo:
    info = RuntimeInfo(pid=os.getpid(), host=settings.host, port=settings.port, token=token)
    _runtime_path(settings).write_text(json.dumps(asdict(info)), encoding="utf-8")
    return info


def read_runtime_info(settings: Settings) -> Optional[RuntimeInfo]:
    path = _runtime_path(settings)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return RuntimeInfo(**data)
    except (json.JSONDecodeError, TypeError, KeyError):
        return None


def clear_runtime_info(settings: Settings) -> None:
    _runtime_path(settings).unlink(missing_ok=True)
