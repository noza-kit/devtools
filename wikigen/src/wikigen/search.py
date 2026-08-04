from __future__ import annotations

import json
import re

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_MAX_TEXT_LENGTH = 2000


def strip_html(html_text: str) -> str:
    """Strip tags and collapse whitespace, leaving plain readable text."""
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", html_text)).strip()


def build_search_index(pages) -> list[dict]:
    return [
        {
            "title": page.title,
            "url": page.output_rel_path,
            "tags": page.tags,
            "text": strip_html(page.html)[:_MAX_TEXT_LENGTH],
        }
        for page in pages
    ]


def render_search_index_js(pages) -> str:
    """Render the search index as a standalone JS file (no fetch/XHR needed)."""
    data = build_search_index(pages)
    return "window.WIKIGEN_SEARCH_INDEX = " + json.dumps(data, ensure_ascii=False) + ";\n"
