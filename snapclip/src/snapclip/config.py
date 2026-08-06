from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional

from confload import load_config

DEFAULT_MODE = "markdown"
DEFAULT_IMG_DIR = "./images"
DEFAULT_CONFIG_PATH = Path.home() / ".snapclip" / "config.yaml"

VALID_MODES = ("markdown", "latex")


@dataclass(frozen=True)
class Settings:
    mode: str = DEFAULT_MODE
    img_dir: Path = Path(DEFAULT_IMG_DIR)

    def __post_init__(self):
        if self.mode not in VALID_MODES:
            raise ValueError(f"invalid mode '{self.mode}' (expected one of {VALID_MODES})")


def load_settings(config_path: Optional[Path] = None) -> Settings:
    """Load snapclip's markup-mode/image-directory settings (confload
    YAML/JSON). Falls back to built-in defaults if `config_path` is not
    given and the default path (`~/.snapclip/config.yaml`) doesn't
    exist; raises if `config_path` is given explicitly but missing."""
    resolved_path = config_path or DEFAULT_CONFIG_PATH

    if resolved_path.exists():
        config = load_config(resolved_path)
        mode = config.get("mode", DEFAULT_MODE)
        img_dir = config.get("img_dir", DEFAULT_IMG_DIR)
    elif config_path is not None:
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")
    else:
        mode, img_dir = DEFAULT_MODE, DEFAULT_IMG_DIR

    return Settings(mode=mode, img_dir=Path(img_dir).expanduser())


def save_settings(settings: Settings, config_path: Optional[Path] = None) -> Path:
    """Persist `settings` as YAML to `config_path` (default: the standard
    `~/.snapclip/config.yaml`), used by `snapclip config --mode ...`."""
    import yaml

    resolved_path = config_path or DEFAULT_CONFIG_PATH
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    data = {"mode": settings.mode, "img_dir": str(settings.img_dir)}
    resolved_path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return resolved_path


def with_overrides(settings: Settings, mode: Optional[str] = None, img_dir: Optional[Path] = None) -> Settings:
    updates = {}
    if mode is not None:
        updates["mode"] = mode
    if img_dir is not None:
        updates["img_dir"] = Path(img_dir).expanduser()
    return replace(settings, **updates)
