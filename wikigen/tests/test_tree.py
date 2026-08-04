from __future__ import annotations

from pathlib import Path

from wikigen.pages import Page
from wikigen.tree import build_sidebar_tree


def _page(rel_path: str, title: str) -> Page:
    return Page(source_path=Path(rel_path), rel_path=Path(rel_path), title=title)


def test_folders_come_before_files_and_both_sorted_alphabetically():
    pages = [
        _page("zeta.md", "Zeta"),
        _page("alpha.md", "Alpha"),
        _page("notes/one.md", "One"),
        _page("archive/old.md", "Old"),
    ]
    tree = build_sidebar_tree(pages)

    assert [n.is_folder for n in tree] == [True, True, False, False]
    assert [n.name for n in tree if n.is_folder] == ["archive", "notes"]
    assert [n.title for n in tree if not n.is_folder] == ["Alpha", "Zeta"]


def test_nested_folder_contains_its_page():
    pages = [_page("notes/sub/deep.md", "Deep Note")]
    tree = build_sidebar_tree(pages)

    assert len(tree) == 1
    notes = tree[0]
    assert notes.is_folder and notes.name == "notes"
    sub = notes.children[0]
    assert sub.is_folder and sub.name == "sub"
    leaf = sub.children[0]
    assert not leaf.is_folder
    assert leaf.title == "Deep Note"
    assert leaf.url == "notes/sub/deep.html"
