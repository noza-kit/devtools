from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class UnsupportedFileTypeError(Exception):
    pass


@dataclass(frozen=True)
class LanguageProfile:
    """Comment syntax for one language family, keyed off file extension."""

    name: str
    line_comment: str | None = None
    block_comment: tuple[str, str] | None = None
    # Quote delimiters that open a string literal, masked out before comment
    # markers are searched for. Longest first so triple quotes win over single.
    string_quotes: tuple[str, ...] = ("\"", "'")
    docstring: bool = False


PYTHON = LanguageProfile(
    name="python",
    line_comment="#",
    string_quotes=('"""', "'''", '"', "'"),
    docstring=True,
)

SHELL = LanguageProfile(
    name="shell",
    line_comment="#",
    string_quotes=('"', "'"),
)

C_FAMILY = LanguageProfile(
    name="c-family",
    line_comment="//",
    block_comment=("/*", "*/"),
    string_quotes=('"', "'", "`"),
)

EXTENSION_PROFILES: dict[str, LanguageProfile] = {
    ".py": PYTHON,
    ".pyw": PYTHON,
    ".sh": SHELL,
    ".bash": SHELL,
    ".zsh": SHELL,
    ".js": C_FAMILY,
    ".jsx": C_FAMILY,
    ".ts": C_FAMILY,
    ".tsx": C_FAMILY,
    ".mjs": C_FAMILY,
    ".cjs": C_FAMILY,
    ".c": C_FAMILY,
    ".h": C_FAMILY,
    ".cpp": C_FAMILY,
    ".cc": C_FAMILY,
    ".hpp": C_FAMILY,
    ".cs": C_FAMILY,
    ".java": C_FAMILY,
    ".go": C_FAMILY,
    ".rs": C_FAMILY,
    ".kt": C_FAMILY,
    ".swift": C_FAMILY,
}


def get_profile(path: str | Path) -> LanguageProfile:
    """Look up the LanguageProfile for `path` by its file extension."""
    suffix = Path(path).suffix.lower()
    try:
        return EXTENSION_PROFILES[suffix]
    except KeyError:
        raise UnsupportedFileTypeError(
            f"Unsupported file extension {suffix or '(none)'!r}: {path}"
        ) from None
