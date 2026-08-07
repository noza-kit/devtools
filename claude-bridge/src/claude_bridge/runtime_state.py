from __future__ import annotations

import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


def default_state_path() -> Path:
    return Path.home() / ".claude-bridge" / "runtime_state.json"


@dataclass
class RuntimeState:
    pid: int
    started_at: str
    current: Optional[str]  # human-readable description of the running task, or None if idle
    queue_length: int


def write_runtime_state(state: RuntimeState, path: Optional[Path] = None) -> None:
    path = path or default_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(state), ensure_ascii=False, indent=2), encoding="utf-8")


def read_runtime_state(path: Optional[Path] = None) -> Optional[RuntimeState]:
    path = path or default_state_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return RuntimeState(**data)


def clear_runtime_state(path: Optional[Path] = None) -> None:
    path = path or default_state_path()
    path.unlink(missing_ok=True)


def is_process_alive(pid: int) -> bool:
    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True, check=False
        )
        return str(pid) in result.stdout
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
