from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from confload import load_config

DEFAULT_TARGET_DIRS = ["~/Downloads", "~/Documents"]
DEFAULT_EXCLUDE = ["venv", ".venv", "node_modules", "__pycache__", ".git"]
DEFAULT_CONFIG_PATH = Path.home() / ".devfind" / "config.yaml"


@dataclass(frozen=True)
class Settings:
    target_dirs: list[Path]
    exclude: list[str]


def load_settings(config_path: Optional[Path] = None) -> Settings:
    """検索対象フォルダ・除外パターンを設定ファイル(confload経由)から読み込む。

    `config_path` が明示されずデフォルトパス(`~/.devfind/config.yaml`)にも
    ファイルが無い場合は、組み込みのデフォルト値(Downloads/Documents、
    venv/node_modules など)にフォールバックする。`config_path` を明示した
    のにファイルが存在しない場合はエラーとする。
    """
    resolved_path = config_path or DEFAULT_CONFIG_PATH

    if resolved_path.exists():
        config = load_config(resolved_path)
        target_dirs = config.get("target_dirs", DEFAULT_TARGET_DIRS)
        exclude = config.get("exclude", DEFAULT_EXCLUDE)
    elif config_path is not None:
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")
    else:
        target_dirs = DEFAULT_TARGET_DIRS
        exclude = DEFAULT_EXCLUDE

    return Settings(
        target_dirs=[Path(d).expanduser() for d in target_dirs],
        exclude=list(exclude),
    )
