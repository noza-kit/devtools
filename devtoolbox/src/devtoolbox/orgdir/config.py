from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

DEFAULT_RULES_FILE = Path(__file__).parent / "rules.yaml"


@dataclass
class OrgdirConfig:
    categories: dict[str, list[str]] = field(default_factory=dict)
    default_category: str = "others"
    no_extension_category: str = "others"
    ignore: list[str] = field(default_factory=list)


def _normalize(raw: dict) -> OrgdirConfig:
    categories_raw = raw.get("categories") or {}
    categories = {
        str(name): [str(ext).lower().lstrip(".") for ext in exts]
        for name, exts in categories_raw.items()
    }
    default_category = raw.get("default_category") or "others"
    return OrgdirConfig(
        categories=categories,
        default_category=default_category,
        no_extension_category=raw.get("no_extension_category") or default_category,
        ignore=list(raw.get("ignore") or []),
    )


def load_orgdir_config(rules_file: Optional[Path] = None) -> OrgdirConfig:
    """Load the extension -> category mapping from `rules_file` (or the bundled default)."""
    path = rules_file if rules_file is not None else DEFAULT_RULES_FILE
    if not path.is_file():
        raise FileNotFoundError(f"Rules file not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return _normalize(raw)
