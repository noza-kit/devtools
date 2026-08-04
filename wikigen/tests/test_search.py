from __future__ import annotations

import json
from pathlib import Path

from wikigen.pages import Page
from wikigen.search import build_search_index, render_search_index_js, strip_html


def test_strip_html_removes_tags_and_collapses_whitespace():
    html = "<h1>Title</h1>\n<p>Hello   <b>world</b></p>"
    assert strip_html(html) == "Title Hello world"


def test_build_search_index_fields():
    page = Page(
        source_path=Path("notes/a.md"),
        rel_path=Path("notes/a.md"),
        title="A Note",
        tags=["x", "y"],
        html="<p>Some content here.</p>",
    )
    index = build_search_index([page])
    assert index == [
        {"title": "A Note", "url": "notes/a.html", "tags": ["x", "y"], "text": "Some content here."}
    ]


def test_render_search_index_js_embeds_valid_json():
    page = Page(
        source_path=Path("a.md"),
        rel_path=Path("a.md"),
        title="Title with \"quotes\"",
        tags=[],
        html="<p>body</p>",
    )
    js = render_search_index_js([page])
    assert js.startswith("window.WIKIGEN_SEARCH_INDEX = ")

    json_text = js[len("window.WIKIGEN_SEARCH_INDEX = ") : -2]
    data = json.loads(json_text)
    assert data[0]["title"] == 'Title with "quotes"'
