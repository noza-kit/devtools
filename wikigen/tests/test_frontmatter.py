from __future__ import annotations

from wikigen.frontmatter import parse_frontmatter


def test_parses_title_and_list_tags():
    text = "---\ntitle: My Note\ntags: [a, b]\n---\n# Body\n\ntext\n"
    meta, body = parse_frontmatter(text)
    assert meta == {"title": "My Note", "tags": ["a", "b"]}
    assert body == "# Body\n\ntext\n"


def test_no_frontmatter_returns_original_text():
    text = "# Just a heading\n\nno frontmatter here\n"
    meta, body = parse_frontmatter(text)
    assert meta == {}
    assert body == text


def test_missing_closing_delimiter_returns_original_text():
    text = "---\ntitle: Oops\nno closing delimiter\n"
    meta, body = parse_frontmatter(text)
    assert meta == {}
    assert body == text


def test_non_mapping_frontmatter_is_ignored():
    text = "---\n- just\n- a\n- list\n---\nbody\n"
    meta, body = parse_frontmatter(text)
    assert meta == {}
    assert body == text


def test_empty_frontmatter_block():
    text = "---\n---\nbody\n"
    meta, body = parse_frontmatter(text)
    assert meta == {}
    assert body == "body\n"
