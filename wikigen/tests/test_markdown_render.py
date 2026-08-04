from __future__ import annotations

from wikigen.markdown_render import render_markdown


def test_renders_heading():
    html = render_markdown("# Title\n")
    # The `toc` extension adds an id to every heading for anchor linking.
    assert '<h1 id="title">Title</h1>' in html


def test_renders_fenced_code_block():
    html = render_markdown("```python\nprint('hi')\n```\n")
    assert "<pre>" in html or "<pre " in html
    assert "print" in html


def test_renders_table_via_extra_extension():
    html = render_markdown("| a | b |\n| - | - |\n| 1 | 2 |\n")
    assert "<table>" in html


def test_renders_paragraph():
    html = render_markdown("hello world\n")
    assert "<p>hello world</p>" in html
