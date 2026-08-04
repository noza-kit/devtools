from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from wikigen.frontmatter import parse_frontmatter


@dataclass
class Page:
    source_path: Path
    rel_path: Path  # relative to the source root, e.g. notes/foo.md
    title: str
    tags: list[str] = field(default_factory=list)
    body: str = ""  # raw markdown body, frontmatter stripped
    html: str = ""  # rendered body HTML, filled in during build

    @property
    def output_rel_path(self) -> str:
        """Output path relative to the site root, posix-style (e.g. notes/foo.html)."""
        return self.rel_path.with_suffix(".html").as_posix()


def discover_pages(source_root: Path) -> list[Page]:
    """Recursively find every *.md file under source_root and parse it into a Page."""
    pages = []
    for md_path in sorted(source_root.rglob("*.md")):
        rel_path = md_path.relative_to(source_root)
        text = md_path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        title = _title(meta, body, rel_path)
        tags = _normalize_tags(meta.get("tags"))
        pages.append(
            Page(source_path=md_path, rel_path=rel_path, title=title, tags=tags, body=body)
        )
    return pages


def _title(meta: dict, body: str, rel_path: Path) -> str:
    meta_title = meta.get("title")
    if isinstance(meta_title, str) and meta_title.strip():
        return meta_title.strip()

    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()

    return rel_path.stem.replace("_", " ").replace("-", " ")


def _normalize_tags(raw) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [t.strip() for t in raw.split(",") if t.strip()]
    if isinstance(raw, (list, tuple)):
        return [str(t).strip() for t in raw if str(t).strip()]
    return []
