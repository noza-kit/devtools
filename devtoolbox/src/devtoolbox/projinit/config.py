from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

TEMPLATES_DIR = Path(__file__).parent / "templates"
LANGUAGES_FILE = TEMPLATES_DIR / "languages.yaml"
GITIGNORE_DIR = TEMPLATES_DIR / "gitignore"
README_TEMPLATE = TEMPLATES_DIR / "readme" / "README.md.j2"


@dataclass
class ExtraFile:
    path: str
    content: str = ""


@dataclass
class LanguageConfig:
    key: str
    display_name: str
    gitignore: str
    extra_files: list[ExtraFile] = field(default_factory=list)

    @property
    def gitignore_path(self) -> Path:
        return GITIGNORE_DIR / self.gitignore


class UnknownLanguageError(ValueError):
    pass


def load_languages() -> dict[str, LanguageConfig]:
    raw = yaml.safe_load(LANGUAGES_FILE.read_text(encoding="utf-8")) or {}
    languages: dict[str, LanguageConfig] = {}
    for key, entry in raw.items():
        extra_files = [ExtraFile(**f) for f in entry.get("extra_files", [])]
        languages[key] = LanguageConfig(
            key=key,
            display_name=entry["display_name"],
            gitignore=entry["gitignore"],
            extra_files=extra_files,
        )
    return languages


def get_language(key: str) -> LanguageConfig:
    languages = load_languages()
    try:
        return languages[key]
    except KeyError as exc:
        available = ", ".join(sorted(languages))
        raise UnknownLanguageError(
            f"Unknown language '{key}'. Available: {available}"
        ) from exc
