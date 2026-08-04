from __future__ import annotations

import pytest

from translate_comments.extractor import extract_comments
from translate_comments.languages import UnsupportedFileTypeError


# --- Python: `#` line comments -------------------------------------------------


def test_standalone_comment(write_source):
    path = write_source("a.py", "# hello world\nx = 1\n")

    blocks = extract_comments(path)

    assert len(blocks) == 1
    b = blocks[0]
    assert b.style == "line"
    assert b.text == "hello world"
    assert b.start_line == 1
    assert b.end_line == 1
    assert b.trailing is False
    assert b.marker_prefix == "#"


def test_adjacent_comment_lines_are_grouped(write_source):
    path = write_source("a.py", "# line one\n# line two\nx = 1\n")

    blocks = extract_comments(path)

    assert len(blocks) == 1
    b = blocks[0]
    assert b.text == "line one\nline two"
    assert b.start_line == 1
    assert b.end_line == 2


def test_blank_line_breaks_grouping(write_source):
    path = write_source("a.py", "# line one\n\n# line two\n")

    blocks = extract_comments(path)

    assert len(blocks) == 2
    assert [b.text for b in blocks] == ["line one", "line two"]


def test_different_indent_breaks_grouping(write_source):
    path = write_source("a.py", "# top level\nif True:\n    # nested\n    pass\n")

    blocks = extract_comments(path)

    assert len(blocks) == 2
    assert blocks[0].text == "top level"
    assert blocks[1].text == "nested"
    assert blocks[1].indent == "    "


def test_comment_marker_inside_string_is_ignored(write_source):
    path = write_source("a.py", 'x = "a # b"\n')

    blocks = extract_comments(path)

    assert blocks == []


def test_trailing_comments_never_merge_even_with_matching_column(write_source):
    path = write_source("a.py", "a = 1  # note one\nb = 2  # note two\n")

    blocks = extract_comments(path)

    assert len(blocks) == 2
    assert blocks[0].trailing is True
    assert blocks[0].text == "note one"
    assert blocks[0].start_line == 1
    assert blocks[1].trailing is True
    assert blocks[1].text == "note two"
    assert blocks[1].start_line == 2


def test_trailing_comment_indent_is_the_code_lines_indent(write_source):
    path = write_source("a.py", "    x = 1  # note\n")

    blocks = extract_comments(path)

    assert len(blocks) == 1
    assert blocks[0].indent == "    "


def test_shebang_is_excluded(write_source):
    path = write_source("a.py", "#!/usr/bin/env python\nx = 1\n")

    assert extract_comments(path) == []


def test_encoding_declaration_is_excluded(write_source):
    path = write_source("a.py", "# -*- coding: utf-8 -*-\nx = 1\n")

    assert extract_comments(path) == []


def test_symbol_only_comment_is_excluded(write_source):
    path = write_source("a.py", "# ----------------\nx = 1\n")

    assert extract_comments(path) == []


# --- Python: docstrings ---------------------------------------------------------


PY_DOCSTRING_SOURCE = '''"""Module docstring."""


class Foo:
    """Class docstring."""

    def bar(self):
        """Function docstring with a # not a comment."""
        return 1


x = """not a docstring, just a string with # inside"""
'''


def test_docstrings_are_extracted_by_scope(write_source):
    path = write_source("a.py", PY_DOCSTRING_SOURCE)

    blocks = extract_comments(path)

    assert len(blocks) == 3
    assert all(b.style == "docstring" for b in blocks)
    assert [b.scope for b in blocks] == ["module", "class", "function"]
    assert [b.text for b in blocks] == [
        "Module docstring.",
        "Class docstring.",
        "Function docstring with a # not a comment.",
    ]
    for b in blocks:
        assert b.marker_prefix == '"""'
        assert b.marker_suffix == '"""'


def test_non_docstring_triple_quoted_string_is_not_extracted(write_source):
    path = write_source("a.py", 'x = """just a value, not a docstring"""\n')

    assert extract_comments(path) == []


def test_docstring_quote_style_and_prefix_are_preserved(write_source):
    path = write_source("a.py", "r'''Raw docstring.'''\n")

    blocks = extract_comments(path)

    assert len(blocks) == 1
    assert blocks[0].marker_prefix == "r'''"
    assert blocks[0].marker_suffix == "'''"
    assert blocks[0].text == "Raw docstring."


def test_docstring_end_col_is_a_character_index_not_a_byte_offset(write_source):
    # ast reports col_offset/end_col_offset in UTF-8 *bytes*. A Japanese
    # docstring is mostly multi-byte characters, so using those offsets
    # directly as `str` slice indices overshoots badly -- which silently
    # swallows the newline after the docstring when the writer reconstructs
    # the file (see test_writer.py for the end-to-end symptom).
    path = write_source(
        "a.py", 'def greet():\n    """名前を受け取り、挨拶文を返す。"""\n    return 1\n'
    )

    blocks = extract_comments(path)

    doc = next(b for b in blocks if b.style == "docstring")
    line = '    """名前を受け取り、挨拶文を返す。"""'
    assert doc.end_col == len(line)
    assert doc.start_col == 4


def test_syntax_error_skips_docstrings_but_keeps_hash_comments(write_source):
    path = write_source("a.py", "# still a comment\ndef broken(:\n")

    blocks = extract_comments(path)

    assert len(blocks) == 1
    assert blocks[0].text == "still a comment"


# --- Shell: `#` without docstrings -----------------------------------------------


def test_shell_hash_comments(write_source):
    path = write_source("deploy.sh", "# deploy script\necho hi\n")

    blocks = extract_comments(path)

    assert len(blocks) == 1
    assert blocks[0].text == "deploy script"


# --- C-family: `//` and `/* */` --------------------------------------------------


def test_c_family_line_comments_are_grouped(write_source):
    path = write_source("a.cpp", "// line one\n// line two\nint x = 1;\n")

    blocks = extract_comments(path)

    assert len(blocks) == 1
    assert blocks[0].text == "line one\nline two"
    assert blocks[0].marker_prefix == "//"


def test_c_family_single_line_block_comment(write_source):
    path = write_source("a.cpp", "/* hello */\nint x = 1;\n")

    blocks = extract_comments(path)

    assert len(blocks) == 1
    assert blocks[0].style == "block"
    assert blocks[0].text == "hello"
    assert blocks[0].marker_prefix == "/*"
    assert blocks[0].marker_suffix == "*/"


def test_c_family_multiline_block_comment(write_source):
    path = write_source("a.cpp", "/*\n * multi\n * line\n */\nint x = 1;\n")

    blocks = extract_comments(path)

    assert len(blocks) == 1
    assert blocks[0].start_line == 1
    assert blocks[0].end_line == 4
    assert "multi" in blocks[0].text
    assert "line" in blocks[0].text


def test_c_family_comment_marker_inside_string_is_ignored(write_source):
    path = write_source("a.cpp", 'char* url = "http://example.com"; // real comment\n')

    blocks = extract_comments(path)

    assert len(blocks) == 1
    assert blocks[0].trailing is True
    assert blocks[0].text == "real comment"


def test_apostrophe_inside_line_comment_does_not_leak_into_next_line(write_source):
    path = write_source("a.cpp", "// don't break here\nint x = 1; // second comment\n")

    blocks = extract_comments(path)

    assert len(blocks) == 2
    assert blocks[0].text == "don't break here"
    assert blocks[0].trailing is False
    assert blocks[1].text == "second comment"
    assert blocks[1].trailing is True


def test_unterminated_block_comment_extracted_to_end_of_file(write_source):
    path = write_source("a.cpp", "/* never closed\nint x = 1;\n")

    blocks = extract_comments(path)

    assert len(blocks) == 1
    assert blocks[0].style == "block"
    assert blocks[0].end_line == 2


# --- Errors -----------------------------------------------------------------------


def test_unsupported_extension_raises(write_source):
    path = write_source("data.json", "{}\n")

    with pytest.raises(UnsupportedFileTypeError):
        extract_comments(path)
