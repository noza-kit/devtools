from datetime import datetime
from pathlib import Path

import pytest

from snapclip.markup import generate_filename, latex_markup, markdown_markup, render_markup


def test_generate_filename_format():
    name = generate_filename(datetime(2026, 3, 4, 15, 30, 45))
    assert name == "20260304_153045.png"


def test_generate_filename_with_suffix():
    name = generate_filename(datetime(2026, 3, 4, 15, 30, 45), suffix="1")
    assert name == "20260304_153045_1.png"


def test_markdown_markup_default_alt():
    # Path("./images/foo.png") normalizes away the leading "./" itself;
    # that's fine for Markdown/LaTeX, both resolve "images/..." the same way.
    assert markdown_markup(Path("./images/foo.png")) == "![スクリーンショット](images/foo.png)"


def test_markdown_markup_custom_alt():
    assert markdown_markup(Path("./images/foo.png"), alt="Fig 1") == "![Fig 1](images/foo.png)"


def test_markdown_markup_uses_forward_slashes(tmp_path: Path):
    windows_path = Path("images") / "foo.png"
    result = markdown_markup(windows_path)
    assert "\\" not in result


def test_latex_markup_structure():
    result = latex_markup(Path("./tex_figures/foo.png"), caption="A caption")
    assert "\\begin{figure}[htbp]" in result
    assert "\\includegraphics[width=\\linewidth]{tex_figures/foo.png}" in result
    assert "\\caption{A caption}" in result
    assert "\\end{figure}" in result


def test_render_markup_dispatches_by_mode():
    assert render_markup("markdown", Path("a.png")).startswith("![")
    assert render_markup("latex", Path("a.png")).startswith("\\begin{figure}")


def test_render_markup_unknown_mode_raises():
    with pytest.raises(ValueError):
        render_markup("html", Path("a.png"))
