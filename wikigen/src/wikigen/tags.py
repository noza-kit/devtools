from __future__ import annotations

import re

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify_tag(tag: str) -> str:
    slug = _SLUG_RE.sub("-", tag.strip().lower()).strip("-")
    return slug or "tag"


def build_tag_index(pages) -> dict[str, list]:
    """Map tag display-name -> pages carrying it, sorted by title.

    Tags are merged case-insensitively (the first-seen casing across pages,
    in discovery order, is used as the display name) so "Python" and
    "python" on different notes land on the same tag page.
    """
    canonical: dict[str, str] = {}
    index: dict[str, list] = {}
    for page in pages:
        for tag in page.tags:
            display = canonical.setdefault(tag.lower(), tag)
            index.setdefault(display, []).append(page)
    for pages_for_tag in index.values():
        pages_for_tag.sort(key=lambda p: p.title.lower())
    return index


def assign_tag_slugs(tag_index: dict[str, list]) -> dict[str, str]:
    """Assign a unique output filename slug to each tag, avoiding collisions.

    "index" is reserved for the tag list page itself; slug clashes between
    distinct tag names (e.g. "C++" and "C") get a numeric suffix.
    """
    used = {"index"}
    result: dict[str, str] = {}
    for name in tag_index:
        base = slugify_tag(name)
        slug = base
        suffix = 2
        while slug in used:
            slug = f"{base}-{suffix}"
            suffix += 1
        used.add(slug)
        result[name] = slug
    return result
