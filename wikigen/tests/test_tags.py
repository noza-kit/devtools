from __future__ import annotations

from pathlib import Path

from wikigen.pages import Page
from wikigen.tags import assign_tag_slugs, build_tag_index, slugify_tag


def _page(rel_path: str, title: str, tags: list[str]) -> Page:
    return Page(source_path=Path(rel_path), rel_path=Path(rel_path), title=title, tags=tags)


def test_slugify_tag_basic():
    assert slugify_tag("Machine Learning") == "machine-learning"
    assert slugify_tag("C++") == "c"
    assert slugify_tag("  spaced  ") == "spaced"


def test_slugify_tag_empty_falls_back():
    assert slugify_tag("###") == "tag"


def test_build_tag_index_groups_case_insensitively_and_sorts_pages():
    pages = [
        _page("b.md", "Bravo", ["Python"]),
        _page("a.md", "Alpha", ["python", "draft"]),
    ]
    index = build_tag_index(pages)

    assert set(index.keys()) == {"Python", "draft"}
    titles = [p.title for p in index["Python"]]
    assert titles == ["Alpha", "Bravo"]


def test_assign_tag_slugs_reserves_index_and_dedupes_collisions():
    pages = [
        _page("a.md", "A", ["index"]),
        _page("b.md", "B", ["C++", "C"]),
    ]
    tag_index = build_tag_index(pages)
    slugs = assign_tag_slugs(tag_index)

    assert slugs["index"] != "index"
    cpp_slug = slugs["C++"]
    c_slug = slugs["C"]
    assert cpp_slug != c_slug
    assert len({slugs["index"], cpp_slug, c_slug}) == 3
