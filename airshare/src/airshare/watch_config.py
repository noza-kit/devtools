from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from confload import load_config

DEFAULT_CONFIG_PATH = Path.home() / ".airshare" / "watch.yaml"
DEFAULT_DEBOUNCE_SECONDS = 3.0
DEFAULT_EXPIRE_DAYS = 7
TEMP_SUFFIXES = (".tmp", ".part", ".crdownload")


@dataclass(frozen=True)
class RoutingRule:
    name: str
    extensions: tuple[str, ...]
    destination: Path


@dataclass(frozen=True)
class CleanupSettings:
    enabled: bool = True
    expire_days: int = DEFAULT_EXPIRE_DAYS


@dataclass(frozen=True)
class WatchSettings:
    inbox_dir: Path
    debounce_seconds: float = DEFAULT_DEBOUNCE_SECONDS
    routing: tuple[RoutingRule, ...] = ()
    hooks: dict[str, str] = field(default_factory=dict)
    cleanup: CleanupSettings = field(default_factory=CleanupSettings)


def load_watch_settings(config_path: Optional[Path], default_inbox_dir: Path) -> WatchSettings:
    """Loads `~/.airshare/watch.yaml` (or `config_path`). `inbox_dir`
    defaults to airshare's own receive_dir (`~/Documents/AirShare/received`,
    or `--receive-dir`/`$AIRSHARE_RECEIVE_DIR`) when the config doesn't
    set one -- this is the same folder `airshare start` already
    delivers iPhone uploads into, matching the spec's "airnotify is
    airshare's companion" framing rather than introducing a second,
    differently-defaulted inbox folder."""
    resolved_path = config_path or DEFAULT_CONFIG_PATH

    if resolved_path.exists():
        config = load_config(resolved_path)
        inbox_dir = Path(config.get("inbox_dir", str(default_inbox_dir))).expanduser()
        debounce_seconds = float(config.get("debounce_seconds", DEFAULT_DEBOUNCE_SECONDS))

        routing = tuple(
            RoutingRule(
                name=name,
                extensions=tuple(e.lower() for e in rule.get("extensions", [])),
                destination=Path(rule["destination"]).expanduser(),
            )
            for name, rule in config.get("routing", {}).items()
        )
        hooks = {ext.lower(): template for ext, template in config.get("hooks", {}).items()}

        cleanup_cfg = config.get("cleanup", {})
        cleanup = CleanupSettings(
            enabled=bool(cleanup_cfg.get("enabled", True)),
            expire_days=int(cleanup_cfg.get("expire_days", DEFAULT_EXPIRE_DAYS)),
        )

        return WatchSettings(
            inbox_dir=inbox_dir, debounce_seconds=debounce_seconds, routing=routing, hooks=hooks, cleanup=cleanup
        )

    if config_path is not None:
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")

    return WatchSettings(inbox_dir=default_inbox_dir)
