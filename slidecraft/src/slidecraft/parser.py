from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from bs4 import BeautifulSoup, NavigableString, Tag

Kind = Literal["paragraph", "bullet"]


@dataclass(frozen=True)
class TextRun:
    text: str
    bold: bool = False
    italic: bool = False


@dataclass(frozen=True)
class ContentItem:
    kind: Kind
    runs: list[TextRun]
    level: int = 0  # bullet indent level (0 = top-level <li>); unused for paragraphs


@dataclass(frozen=True)
class ImageRef:
    path: Path  # resolved absolute path (relative `src` values are resolved against the HTML file's directory)
    alt: str = ""


@dataclass(frozen=True)
class SlideData:
    title: str
    content_items: list[ContentItem] = field(default_factory=list)
    images: list[ImageRef] = field(default_factory=list)
    notes: str = ""


class SlideParseError(ValueError):
    pass


def parse_html(html_path: Path) -> list[SlideData]:
    """Parse an HTML file matching slidecraft's expected structure (see
    README's "HTML ⇔ スライド マッピング定義") into one SlideData per
    `<section class="slide">`. Image `src` paths are resolved relative
    to `html_path`'s own directory."""
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    sections = soup.select("section.slide")
    if not sections:
        raise SlideParseError(f'no <section class="slide"> elements found in {html_path}')
    return [_parse_slide(section, html_path.parent) for section in sections]


def _parse_slide(section: Tag, base_dir: Path) -> SlideData:
    h1 = section.find("h1")
    title = h1.get_text(strip=True) if h1 else ""

    notes_el = section.find("aside", class_="notes")
    notes = notes_el.get_text(strip=True) if notes_el else ""

    content_root = section.find("div", class_="content") or section
    excluded = {id(h1), id(notes_el)} if content_root is section else set()

    content_items: list[ContentItem] = []
    images: list[ImageRef] = []
    for child in content_root.find_all(["ul", "ol", "p", "img"], recursive=True):
        if id(child) in excluded:
            continue
        if _is_nested_in(child, ("ul", "ol")) and child.name in ("ul", "ol"):
            continue  # nested lists are walked from their parent <li>, not as top-level items
        if child.name in ("ul", "ol"):
            _process_list(child, content_items, level=0)
        elif child.name == "p":
            if not _is_nested_in(child, ("ul", "ol")):
                content_items.append(ContentItem(kind="paragraph", runs=_extract_runs(child)))
        elif child.name == "img":
            src = child.get("src", "")
            if src:
                images.append(ImageRef(path=_resolve_image_path(src, base_dir), alt=child.get("alt", "")))

    return SlideData(title=title, content_items=content_items, images=images, notes=notes)


def _is_nested_in(tag: Tag, ancestor_names: tuple[str, ...]) -> bool:
    return any(parent.name in ancestor_names for parent in tag.parents)


def _process_list(list_el: Tag, items: list[ContentItem], level: int) -> None:
    for li in list_el.find_all("li", recursive=False):
        items.append(ContentItem(kind="bullet", runs=_extract_runs(li, stop_tags=("ul", "ol")), level=level))
        for nested in li.find_all(["ul", "ol"], recursive=False):
            _process_list(nested, items, level + 1)


def _extract_runs(el: Tag, stop_tags: tuple[str, ...] = ()) -> list[TextRun]:
    runs: list[TextRun] = []

    def walk(node, bold: bool, italic: bool) -> None:
        for child in node.children:
            if isinstance(child, NavigableString):
                text = str(child)
                if text.strip():
                    runs.append(TextRun(text=text.strip(), bold=bold, italic=italic))
            elif isinstance(child, Tag):
                if child.name in stop_tags:
                    continue
                if child.name in ("strong", "b"):
                    walk(child, True, italic)
                elif child.name in ("em", "i"):
                    walk(child, bold, True)
                else:
                    walk(child, bold, italic)

    walk(el, False, False)
    return runs


def _resolve_image_path(src: str, base_dir: Path) -> Path:
    path = Path(src)
    return path if path.is_absolute() else (base_dir / path).resolve()
