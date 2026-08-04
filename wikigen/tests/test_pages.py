from __future__ import annotations

from pathlib import Path

from wikigen.pages import discover_pages


def test_discover_pages_finds_all_md_files_recursively(sample_source: Path):
    pages = discover_pages(sample_source)
    rel_paths = sorted(p.rel_path.as_posix() for p in pages)
    assert rel_paths == ["index.md", "notes/second.md", "notes/third.md"]


def test_frontmatter_title_and_tags(sample_source: Path):
    pages = {p.rel_path.as_posix(): p for p in discover_pages(sample_source)}
    home = pages["index.md"]
    assert home.title == "Home"
    assert home.tags == ["general"]

    second = pages["notes/second.md"]
    assert second.title == "Second Note"
    assert second.tags == ["general", "draft"]


def test_title_falls_back_to_h1_then_filename(tmp_path: Path):
    source = tmp_path / "src"
    source.mkdir()
    (source / "has_h1.md").write_text("# Heading Title\n\nbody\n", encoding="utf-8")
    (source / "no_heading.md").write_text("just a paragraph\n", encoding="utf-8")

    pages = {p.rel_path.name: p for p in discover_pages(source)}
    assert pages["has_h1.md"].title == "Heading Title"
    assert pages["no_heading.md"].title == "no heading"


def test_tags_normalized_from_comma_string(tmp_path: Path):
    source = tmp_path / "src"
    source.mkdir()
    (source / "a.md").write_text("---\ntags: foo, bar\n---\nbody\n", encoding="utf-8")
    page = discover_pages(source)[0]
    assert page.tags == ["foo", "bar"]


def test_output_rel_path_swaps_extension(sample_source: Path):
    pages = {p.rel_path.as_posix(): p for p in discover_pages(sample_source)}
    assert pages["notes/second.md"].output_rel_path == "notes/second.html"
