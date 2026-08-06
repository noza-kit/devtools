from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from confload import load_config

DEFAULT_TARGET_DIRS = ["~/Documents"]
DEFAULT_EXCLUDE = ["venv", ".venv", "node_modules", "__pycache__", ".git"]
DEFAULT_EXTENSIONS = [".md", ".txt", ".csv"]
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50
DEFAULT_EDITOR_COMMAND = "code -g {path}:{line}"
DEFAULT_CONFIG_PATH = Path.home() / ".notesearch" / "config.yaml"
DEFAULT_DB_DIR = Path.home() / ".notesearch" / "db"


@dataclass(frozen=True)
class Settings:
    target_dirs: list[Path] = field(default_factory=lambda: [Path(d).expanduser() for d in DEFAULT_TARGET_DIRS])
    exclude: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDE))
    extensions: list[str] = field(default_factory=lambda: list(DEFAULT_EXTENSIONS))
    auto_convert_pdf: bool = False
    chunk_size: int = DEFAULT_CHUNK_SIZE
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    editor_command: str = DEFAULT_EDITOR_COMMAND
    db_dir: Path = field(default_factory=lambda: DEFAULT_DB_DIR)
    gemini_api_key: Optional[str] = None


def load_settings(config_path: Optional[Path] = None) -> Settings:
    """Same hybrid-with-fallback resolution as devfind's load_settings:
    an explicit `config_path` must exist; otherwise the default path is
    used if present, else built-in defaults."""
    resolved_path = config_path or DEFAULT_CONFIG_PATH

    if resolved_path.exists():
        config = load_config(resolved_path)
        return Settings(
            target_dirs=[Path(d).expanduser() for d in config.get("target_dirs", DEFAULT_TARGET_DIRS)],
            exclude=list(config.get("exclude", DEFAULT_EXCLUDE)),
            extensions=list(config.get("extensions", DEFAULT_EXTENSIONS)),
            auto_convert_pdf=bool(config.get("auto_convert_pdf", False)),
            chunk_size=int(config.get("chunk_size", DEFAULT_CHUNK_SIZE)),
            chunk_overlap=int(config.get("chunk_overlap", DEFAULT_CHUNK_OVERLAP)),
            editor_command=config.get("editor_command", DEFAULT_EDITOR_COMMAND),
            db_dir=Path(config.get("db_dir", DEFAULT_DB_DIR)).expanduser(),
            gemini_api_key=config.get("gemini_api_key"),
        )
    if config_path is not None:
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")
    return Settings()
