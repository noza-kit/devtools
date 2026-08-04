from __future__ import annotations

import shutil
from importlib import resources
from pathlib import Path

from wikigen.markdown_render import render_markdown
from wikigen.pages import Page, discover_pages
from wikigen.render import (
    render_fallback_index_html,
    render_page_html,
    render_tag_index_html,
    render_tag_page_html,
)
from wikigen.search import render_search_index_js
from wikigen.tags import assign_tag_slugs, build_tag_index
from wikigen.tree import build_sidebar_tree
from wikigen.wikilinks import build_wikilink_index, resolve_wikilinks

SITE_TITLE = "Wiki"


def build_site(source: Path, output: Path, site_title: str = SITE_TITLE) -> list[Page]:
    """Build a static searchable HTML wiki from a folder of Markdown notes.

    Returns the list of discovered/rendered Page objects.
    """
    source = Path(source)
    output = Path(output)
    if not source.is_dir():
        raise FileNotFoundError(f"Markdown source folder not found: {source}")

    pages = discover_pages(source)
    if not pages:
        raise ValueError(f"No .md files found under: {source}")

    link_index = build_wikilink_index(pages)
    for page in pages:
        raw_html = render_markdown(page.body)
        page.html = resolve_wikilinks(raw_html, page.output_rel_path, link_index)

    output.mkdir(parents=True, exist_ok=True)
    tree = build_sidebar_tree(pages)
    tag_index = build_tag_index(pages)
    tag_slug_by_name = assign_tag_slugs(tag_index)

    _write_assets(output)
    _write_search_index(output, pages)
    _write_pages(output, pages, tree, tag_slug_by_name, site_title)
    _write_tag_pages(output, tag_index, tag_slug_by_name, tree, site_title)

    has_index = any(p.rel_path.as_posix() == "index.md" for p in pages)
    if not has_index:
        (output / "index.html").write_text(
            render_fallback_index_html(pages, tree, site_title), encoding="utf-8"
        )

    return pages


def _write_assets(output: Path) -> None:
    assets_dir = output / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    static_dir = resources.files("wikigen") / "static"
    for name in ("style.css", "search.js"):
        with resources.as_file(static_dir / name) as src_path:
            shutil.copy(str(src_path), str(assets_dir / name))


def _write_search_index(output: Path, pages: list[Page]) -> None:
    (output / "assets" / "search-index.js").write_text(
        render_search_index_js(pages), encoding="utf-8"
    )


def _write_pages(output: Path, pages: list[Page], tree, tag_slug_by_name, site_title: str) -> None:
    for page in pages:
        html_out = render_page_html(page, tree, tag_slug_by_name, site_title)
        dest = output / page.output_rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html_out, encoding="utf-8")


def _write_tag_pages(output: Path, tag_index, tag_slug_by_name, tree, site_title: str) -> None:
    tags_dir = output / "tags"
    tags_dir.mkdir(parents=True, exist_ok=True)

    (tags_dir / "index.html").write_text(
        render_tag_index_html(tag_index, tag_slug_by_name, tree, site_title), encoding="utf-8"
    )
    for name, pages_for_tag in tag_index.items():
        slug = tag_slug_by_name[name]
        (tags_dir / f"{slug}.html").write_text(
            render_tag_page_html(name, pages_for_tag, tree, site_title), encoding="utf-8"
        )
