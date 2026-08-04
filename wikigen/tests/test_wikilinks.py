from __future__ import annotations

from pathlib import Path

from wikigen.pages import Page
from wikigen.wikilinks import build_wikilink_index, resolve_wikilinks


def _page(rel_path: str, title: str) -> Page:
    return Page(source_path=Path(rel_path), rel_path=Path(rel_path), title=title)


def test_resolves_link_by_title_with_relative_href_across_dirs():
    pages = [_page("index.md", "Home"), _page("notes/second.md", "Second Note")]
    index = build_wikilink_index(pages)

    # Link from the root page down into a subdirectory.
    html = resolve_wikilinks("<p>[[Second Note]]</p>", "index.html", index)
    assert 'href="notes/second.html"' in html
    assert 'class="wikilink"' in html

    # Link from the subdirectory page back up to the root.
    html = resolve_wikilinks("<p>[[Home]]</p>", "notes/second.html", index)
    assert 'href="../index.html"' in html


def test_alias_syntax_uses_display_text():
    pages = [_page("notes/second.md", "Second Note")]
    index = build_wikilink_index(pages)
    html = resolve_wikilinks("[[Second Note|click here]]", "index.html", index)
    assert ">click here</a>" in html
    assert 'href="notes/second.html"' in html


def test_unresolved_link_gets_broken_class_and_no_href():
    index = build_wikilink_index([])
    html = resolve_wikilinks("[[Nope]]", "index.html", index)
    assert "wikilink-broken" in html
    assert "href=" not in html


def test_matches_by_filename_stem_when_title_differs():
    pages = [_page("notes/second.md", "A Different Title")]
    index = build_wikilink_index(pages)
    html = resolve_wikilinks("[[second]]", "index.html", index)
    assert 'href="notes/second.html"' in html


def test_wikilink_inside_pre_block_is_not_converted():
    html_in = "<pre><code>[[literal text]]</code></pre>"
    index = build_wikilink_index([])
    html_out = resolve_wikilinks(html_in, "index.html", index)
    assert html_out == html_in


def test_wikilink_inside_inline_code_is_not_converted():
    html_in = "<p>Use <code>[[Foo]]</code> syntax.</p>"
    index = build_wikilink_index([])
    html_out = resolve_wikilinks(html_in, "index.html", index)
    assert html_out == html_in
