from __future__ import annotations

import re
from pathlib import Path

import pytest

from wikigen.core import build_site


def _page_list_section(html: str) -> str:
    match = re.search(r'<ul class="wikigen-page-list">.*?</ul>', html, re.DOTALL)
    assert match, "expected a wikigen-page-list section in the rendered tag page"
    return match.group(0)


def test_build_site_raises_for_missing_source(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        build_site(tmp_path / "does-not-exist", tmp_path / "out")


def test_build_site_raises_for_empty_source(tmp_path: Path):
    source = tmp_path / "empty"
    source.mkdir()
    with pytest.raises(ValueError):
        build_site(source, tmp_path / "out")


def test_build_site_writes_expected_files(sample_source: Path, tmp_path: Path):
    output = tmp_path / "out"
    build_site(sample_source, output)

    assert (output / "index.html").exists()
    assert (output / "notes" / "second.html").exists()
    assert (output / "notes" / "third.html").exists()
    assert (output / "assets" / "style.css").exists()
    assert (output / "assets" / "search.js").exists()
    assert (output / "assets" / "search-index.js").exists()
    assert (output / "tags" / "index.html").exists()
    assert (output / "tags" / "general.html").exists()
    assert (output / "tags" / "draft.html").exists()


def test_build_site_resolves_wikilinks_between_pages(sample_source: Path, tmp_path: Path):
    output = tmp_path / "out"
    build_site(sample_source, output)

    index_html = (output / "index.html").read_text(encoding="utf-8")
    assert 'href="notes/second.html"' in index_html

    second_html = (output / "notes" / "second.html").read_text(encoding="utf-8")
    assert 'href="../index.html"' in second_html


def test_build_site_marks_broken_wikilink_and_skips_code_block(sample_source: Path, tmp_path: Path):
    output = tmp_path / "out"
    build_site(sample_source, output)

    third_html = (output / "notes" / "third.html").read_text(encoding="utf-8")
    assert "wikilink-broken" in third_html
    # The literal syntax inside the fenced code block must survive untouched.
    assert "[[not a real link]]" in third_html


def test_build_site_tag_pages_list_correct_notes(sample_source: Path, tmp_path: Path):
    output = tmp_path / "out"
    build_site(sample_source, output)

    general_html = (output / "tags" / "general.html").read_text(encoding="utf-8")
    assert "Home" in general_html
    assert "Second Note" in general_html

    draft_html = (output / "tags" / "draft.html").read_text(encoding="utf-8")
    draft_list = _page_list_section(draft_html)
    assert "Second Note" in draft_list
    assert "Home" not in draft_list


def test_build_site_generates_fallback_index_when_no_index_md(tmp_path: Path):
    source = tmp_path / "src"
    source.mkdir()
    (source / "only.md").write_text("# Only Page\n\nbody\n", encoding="utf-8")

    output = tmp_path / "out"
    build_site(source, output)

    index_html = (output / "index.html").read_text(encoding="utf-8")
    assert 'href="only.html"' in index_html


def test_build_site_does_not_overwrite_real_index_md(sample_source: Path, tmp_path: Path):
    output = tmp_path / "out"
    build_site(sample_source, output)

    index_html = (output / "index.html").read_text(encoding="utf-8")
    assert "Welcome" in index_html
