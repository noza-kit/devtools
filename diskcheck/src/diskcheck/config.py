from __future__ import annotations

from pathlib import Path
from typing import Optional

from confload import load_config

DEFAULT_STALE_EXTENSIONS = [".dmg", ".exe", ".msi", ".pkg", ".deb", ".AppImage"]


def normalize_extension(ext: str) -> str:
    ext = ext.strip().lower()
    if not ext.startswith("."):
        ext = "." + ext
    return ext


def load_stale_extensions(config_path: Optional[Path] = None) -> list[str]:
    """Return the configured set of "stale installer" extensions.

    Without `config_path`, returns `DEFAULT_STALE_EXTENSIONS`. Otherwise loads
    a YAML/JSON config file (via confload) with a top-level `extensions` list.
    """
    if config_path is None:
        return [normalize_extension(e) for e in DEFAULT_STALE_EXTENSIONS]

    config = load_config(config_path)
    extensions = config.get("extensions", DEFAULT_STALE_EXTENSIONS)
    return [normalize_extension(e) for e in extensions]
