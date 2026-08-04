from __future__ import annotations

from pathlib import Path

from translate_comments.extractor import extract_comments
from translate_comments.writer import render_inline, render_separate, separate_output_path


def _extract(write_source, name, content):
    path = write_source(name, content)
    return path.read_text(encoding="utf-8"), extract_comments(path)


# --- render_inline ------------------------------------------------------------------


def test_inline_standalone_comment(write_source):
    text, blocks = _extract(write_source, "a.py", "# hello\nx = 1\n")

    out = render_inline(text, blocks, {"en": ["Hello"]}, ["en"])

    assert out == "# hello\n# [EN] Hello\nx = 1\n"


def test_inline_multiple_targets_in_requested_order(write_source):
    text, blocks = _extract(write_source, "a.py", "# hello\nx = 1\n")

    out = render_inline(text, blocks, {"en": ["Hello"], "fr": ["Bonjour"]}, ["en", "fr"])

    assert out == "# hello\n# [EN] Hello\n# [FR] Bonjour\nx = 1\n"


def test_inline_trailing_comment_inserts_below_with_code_indent(write_source):
    text, blocks = _extract(write_source, "a.py", "    x = 1  # note\n")

    out = render_inline(text, blocks, {"en": ["Translated note"]}, ["en"])

    assert out == "    x = 1  # note\n    # [EN] Translated note\n"


def test_inline_multiline_grouped_comment_only_tags_first_line(write_source):
    text, blocks = _extract(write_source, "a.py", "# line one\n# line two\nx = 1\n")

    out = render_inline(
        text, blocks, {"en": ["Translated one\nTranslated two"]}, ["en"]
    )

    assert out == (
        "# line one\n# line two\n"
        "# [EN] Translated one\n# Translated two\n"
        "x = 1\n"
    )


def test_inline_block_comment_single_line(write_source):
    text, blocks = _extract(write_source, "a.cpp", "/* hello */\nint x = 1;\n")

    out = render_inline(text, blocks, {"en": ["Hello"]}, ["en"])

    assert out == "/* hello */\n/* [EN] Hello */\nint x = 1;\n"


def test_inline_block_comment_multiline_translation(write_source):
    text, blocks = _extract(write_source, "a.cpp", "/* hello */\nint x = 1;\n")

    out = render_inline(text, blocks, {"en": ["Hello\nWorld"]}, ["en"])

    assert out == (
        "/* hello */\n"
        "/*\n [EN] Hello\n World\n*/\n"
        "int x = 1;\n"
    )


def test_inline_docstring_uses_hash_marker_not_a_second_docstring(write_source):
    text, blocks = _extract(write_source, "a.py", '"""Module doc."""\nx = 1\n')

    out = render_inline(text, blocks, {"en": ["Module documentation."]}, ["en"])

    assert out == '"""Module doc."""\n# [EN] Module documentation.\nx = 1\n'


def test_inline_never_modifies_original_lines(write_source):
    original = "# a\n# b\nx = 1  # c\n"
    text, blocks = _extract(write_source, "a.py", original)

    out = render_inline(
        text, blocks, {"en": ["A", "C"]}, ["en"]
    )

    for line in original.splitlines():
        assert line in out.splitlines()


# --- render_separate ------------------------------------------------------------------


def test_separate_does_not_merge_japanese_docstring_with_following_comment(write_source):
    # Regression test: a Japanese docstring's end_col used to be a UTF-8 byte
    # offset used as a str index, which overshot the line and silently ate
    # the trailing newline -- merging the next line's comment onto the same
    # line as the docstring (and shifting the code below it up by one line).
    text, blocks = _extract(
        write_source,
        "a.py",
        'def greet():\n    """名前を受け取り、挨拶文を返す。"""\n    # 挨拶のベースになる文字列を作る\n    return 1\n',
    )

    out = render_separate(text, blocks, ["Return a greeting.", "Build the base string"])

    assert out == (
        'def greet():\n'
        '    """Return a greeting."""\n'
        '    # Build the base string\n'
        '    return 1\n'
    )


def test_separate_replaces_standalone_comment(write_source):
    text, blocks = _extract(write_source, "a.py", "# hello\nx = 1\n")

    out = render_separate(text, blocks, ["Hello"])

    assert out == "# Hello\nx = 1\n"


def test_separate_collapsing_multiline_group_to_one_line(write_source):
    text, blocks = _extract(write_source, "a.py", "# line one\n# line two\nx = 1\n")

    out = render_separate(text, blocks, ["Translated single line"])

    assert out == "# Translated single line\nx = 1\n"


def test_separate_preserves_code_around_trailing_comment(write_source):
    text, blocks = _extract(write_source, "a.py", "x = 1  # note\n")

    out = render_separate(text, blocks, ["translated note"])

    assert out == "x = 1  # translated note\n"


def test_separate_replaces_docstring_keeping_quote_style(write_source):
    text, blocks = _extract(write_source, "a.py", '"""Module doc."""\nx = 1\n')

    out = render_separate(text, blocks, ["Module documentation."])

    assert out == '"""Module documentation."""\nx = 1\n'


def test_separate_does_not_touch_unrelated_lines(write_source):
    text, blocks = _extract(
        write_source, "a.py", "# first\ny = 2\n# second\nz = 3\n"
    )

    out = render_separate(text, blocks, ["First", "Second"])

    assert out == "# First\ny = 2\n# Second\nz = 3\n"


def test_separate_multiple_blocks_do_not_interfere(write_source):
    text, blocks = _extract(
        write_source, "a.cpp", "// one\nint a;\n/* two */\nint b;\n"
    )

    out = render_separate(text, blocks, ["ONE", "TWO"])

    assert out == "// ONE\nint a;\n/* TWO */\nint b;\n"


# --- separate_output_path -------------------------------------------------------------


def test_separate_output_path():
    assert separate_output_path(Path("dir/file.py"), "en") == Path("dir/file_en.py")
    assert separate_output_path("app.js", "fr") == Path("app_fr.js")
