from __future__ import annotations

import json
import os
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

RUNTIME_DIR = Path.home() / ".airshare"
WATCH_RUNTIME_FILENAME = "watch_run.json"
WATCH_LOG_FILENAME = "watch_log.jsonl"
MAX_LOG_ENTRIES = 500


@dataclass(frozen=True)
class WatchRuntimeInfo:
    pid: int
    started_at: str


def _runtime_path() -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    return RUNTIME_DIR / WATCH_RUNTIME_FILENAME


def write_watch_runtime_info() -> WatchRuntimeInfo:
    info = WatchRuntimeInfo(pid=os.getpid(), started_at=datetime.now(timezone.utc).isoformat())
    _runtime_path().write_text(json.dumps(asdict(info)), encoding="utf-8")
    return info


def read_watch_runtime_info() -> Optional[WatchRuntimeInfo]:
    path = _runtime_path()
    if not path.exists():
        return None
    try:
        return WatchRuntimeInfo(**json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, TypeError, KeyError):
        return None


def clear_watch_runtime_info() -> None:
    _runtime_path().unlink(missing_ok=True)


def is_process_alive(pid: int) -> bool:
    if os.name == "nt":
        result = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True)
        return str(pid) in result.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def append_log_entry(message: str, file_count: int, log_path: Optional[Path] = None) -> None:
    path = log_path or (RUNTIME_DIR / WATCH_LOG_FILENAME)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "message": message, "file_count": file_count}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    _trim_log(path)


def _trim_log(path: Path, max_entries: Optional[int] = None) -> None:
    # Resolved here (not as a default-argument value) so monkeypatching
    # module-level MAX_LOG_ENTRIES in tests takes effect.
    max_entries = max_entries if max_entries is not None else MAX_LOG_ENTRIES
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) > max_entries:
        path.write_text("\n".join(lines[-max_entries:]) + "\n", encoding="utf-8")


def read_recent_log_entries(within_hours: float = 24.0, log_path: Optional[Path] = None, now: Optional[float] = None) -> list[dict]:
    path = log_path or (RUNTIME_DIR / WATCH_LOG_FILENAME)
    if not path.exists():
        return []

    cutoff = (now if now is not None else datetime.now(timezone.utc).timestamp()) - within_hours * 3600
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
            if datetime.fromisoformat(entry["timestamp"]).timestamp() >= cutoff:
                entries.append(entry)
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    return entries
