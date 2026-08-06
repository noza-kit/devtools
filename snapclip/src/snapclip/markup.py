from __future__ import annotations

from datetime import datetime
from pathlib import Path

FILENAME_FORMAT = "%Y%m%d_%H%M%S"


def generate_filename(now: datetime | None = None, suffix: str = "") -> str:
    """"YYYYMMDD_HHMMSS.png", or "YYYYMMDD_HHMMSS_<suffix>.png" when two
    captures land in the same second (suffix is a disambiguator, e.g.
    "1", "2", ...)."""
    stamp = (now or datetime.now()).strftime(FILENAME_FORMAT)
    return f"{stamp}_{suffix}.png" if suffix else f"{stamp}.png"


def markdown_markup(image_path: Path, alt: str = "スクリーンショット") -> str:
    return f"![{alt}]({_relative_slash_path(image_path)})"


def latex_markup(image_path: Path, caption: str = "") -> str:
    return (
        "\\begin{figure}[htbp]\n"
        "    \\centering\n"
        f"    \\includegraphics[width=\\linewidth]{{{_relative_slash_path(image_path)}}}\n"
        f"    \\caption{{{caption}}}\n"
        "\\end{figure}"
    )


def render_markup(mode: str, image_path: Path, **kwargs) -> str:
    if mode == "markdown":
        return markdown_markup(image_path, **kwargs)
    if mode == "latex":
        return latex_markup(image_path, **kwargs)
    raise ValueError(f"unknown markup mode '{mode}' (expected 'markdown' or 'latex')")


def _relative_slash_path(path: Path) -> str:
    """Render a path with forward slashes regardless of platform, since
    it's going into a Markdown/LaTeX document, not a shell command."""
    return str(path).replace("\\", "/")
