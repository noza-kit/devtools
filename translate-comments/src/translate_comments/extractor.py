from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from translate_comments.languages import LanguageProfile, get_profile

Style = Literal["line", "block", "docstring"]
Scope = Literal["module", "class", "function"]

# PEP 263 encoding declaration, e.g. `# -*- coding: utf-8 -*-`; only meaningful
# on line 1 or 2 and never worth sending to a translation API.
_ENCODING_DECL_RE = re.compile(r"coding[:=]\s*[-\w.]+")

_DOCSTRING_SCOPES: dict[type, Scope] = {
    ast.Module: "module",
    ast.ClassDef: "class",
    ast.FunctionDef: "function",
    ast.AsyncFunctionDef: "function",
}


@dataclass
class CommentBlock:
    """One translatable unit: a run of adjacent line comments, a single block
    comment, or (Python only) a docstring."""

    style: Style
    marker_prefix: str
    marker_suffix: str
    start_line: int  # 1-indexed, inclusive
    end_line: int
    start_col: int  # 0-indexed
    end_col: int
    indent: str  # leading whitespace of the comment's (or code's, if trailing) line
    trailing: bool  # True if code precedes the comment on its start line
    text: str  # comment body with markers stripped, ready to translate
    scope: Scope | None = None  # docstring only: which kind of definition it documents


@dataclass
class _RawComment:
    style: Literal["line", "block"]
    start_line: int
    end_line: int
    start_col: int
    end_col: int
    text: str
    trailing: bool


def extract_comments(path: str | Path) -> list[CommentBlock]:
    """Extract translatable comments (and Python docstrings) from a source file.

    Only comment/docstring text is returned; the code around it is never
    touched. Comment markers found inside string literals are ignored via
    best-effort string masking (not a full parser) -- see module docs for
    known limitations (raw/verbatim string escaping, template literal
    interpolations).
    """
    path = Path(path)
    profile = get_profile(path)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    raw = _scan_raw(text, profile)
    blocks = _group_line_comments(raw, profile, lines)

    if profile.docstring:
        blocks += _extract_docstrings(text, path, lines)

    blocks.sort(key=lambda b: (b.start_line, b.start_col))
    return [b for b in blocks if _is_translatable(b)]


def _scan_raw(text: str, profile: LanguageProfile) -> list[_RawComment]:
    """Single left-to-right pass that masks string literals and pulls out
    line/block comments outside of them, tracking line/column as it goes."""
    results: list[_RawComment] = []
    n = len(text)
    i = 0
    line = 1
    col0 = 0  # index of the current line's first character

    state: Literal["code", "string", "block_comment"] = "code"
    string_delim = ""
    escape_pending = False
    close_marker = ""
    block_start_line = 0
    block_start_col = 0
    block_body_start = 0
    block_trailing = False

    while i < n:
        ch = text[i]

        if ch == "\n":
            if state == "string":
                escape_pending = False  # backslash-newline line continuation, consumed
            line += 1
            i += 1
            col0 = i
            continue

        if state == "string":
            if escape_pending:
                escape_pending = False
                i += 1
            elif ch == "\\":
                escape_pending = True
                i += 1
            elif text.startswith(string_delim, i):
                i += len(string_delim)
                state = "code"
                string_delim = ""
            else:
                i += 1
            continue

        if state == "block_comment":
            if text.startswith(close_marker, i):
                body = text[block_body_start:i]
                results.append(_RawComment(
                    style="block",
                    start_line=block_start_line,
                    end_line=line,
                    start_col=block_start_col,
                    end_col=(i - col0) + len(close_marker),
                    text=body,
                    trailing=block_trailing,
                ))
                i += len(close_marker)
                state = "code"
            else:
                i += 1
            continue

        # state == "code"
        matched_quote = next((q for q in profile.string_quotes if text.startswith(q, i)), None)
        if matched_quote:
            state = "string"
            string_delim = matched_quote
            i += len(matched_quote)
            continue

        if profile.block_comment and text.startswith(profile.block_comment[0], i):
            block_start_line = line
            block_start_col = i - col0
            block_trailing = bool(text[col0:i].strip())
            block_body_start = i + len(profile.block_comment[0])
            close_marker = profile.block_comment[1]
            state = "block_comment"
            i = block_body_start
            continue

        if profile.line_comment and text.startswith(profile.line_comment, i):
            eol = text.find("\n", i)
            if eol == -1:
                eol = n
            body_start = i + len(profile.line_comment)
            results.append(_RawComment(
                style="line",
                start_line=line,
                end_line=line,
                start_col=i - col0,
                end_col=eol - col0,
                text=text[body_start:eol],
                trailing=bool(text[col0:i].strip()),
            ))
            i = eol
            continue

        i += 1

    if state == "block_comment":
        # Unterminated block comment: surface what we have rather than dropping it.
        # A trailing "\n" at EOF bumps `line` past the last real source line, so
        # clamp back to the file's actual line count.
        total_lines = len(text.splitlines())
        end_line = min(line, total_lines) if total_lines else line
        results.append(_RawComment(
            style="block",
            start_line=block_start_line,
            end_line=end_line,
            start_col=block_start_col,
            end_col=n - col0,
            text=text[block_body_start:n],
            trailing=block_trailing,
        ))

    return results


def _group_line_comments(
    raw: list[_RawComment], profile: LanguageProfile, lines: list[str]
) -> list[CommentBlock]:
    """Merge adjacent standalone `#`/`//` lines (same style, same indent, no
    gap) into one translation unit; trailing comments never merge, since
    they're tied to the specific code line they follow."""
    blocks: list[CommentBlock] = []

    line_raws = [r for r in raw if r.style == "line"]
    i = 0
    while i < len(line_raws):
        group = [line_raws[i]]
        i += 1
        if not group[0].trailing:
            while (
                i < len(line_raws)
                and not line_raws[i].trailing
                and line_raws[i].start_col == group[0].start_col
                and line_raws[i].start_line == group[-1].start_line + 1
            ):
                group.append(line_raws[i])
                i += 1

        blocks.append(CommentBlock(
            style="line",
            marker_prefix=profile.line_comment or "",
            marker_suffix="",
            start_line=group[0].start_line,
            end_line=group[-1].end_line,
            start_col=group[0].start_col,
            end_col=group[-1].end_col,
            indent=_leading_whitespace(lines, group[0].start_line),
            trailing=group[0].trailing,
            text="\n".join(r.text.strip() for r in group),
        ))

    for r in raw:
        if r.style != "block":
            continue
        assert profile.block_comment is not None
        blocks.append(CommentBlock(
            style="block",
            marker_prefix=profile.block_comment[0],
            marker_suffix=profile.block_comment[1],
            start_line=r.start_line,
            end_line=r.end_line,
            start_col=r.start_col,
            end_col=r.end_col,
            indent=_leading_whitespace(lines, r.start_line),
            trailing=r.trailing,
            text=r.text.strip(),
        ))

    return blocks


def _leading_whitespace(lines: list[str], line_no: int) -> str:
    if line_no - 1 >= len(lines):
        return ""
    line_text = lines[line_no - 1]
    return line_text[: len(line_text) - len(line_text.lstrip(" \t"))]


def _extract_docstrings(text: str, path: Path, lines: list[str]) -> list[CommentBlock]:
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return []

    blocks: list[CommentBlock] = []
    for node in ast.walk(tree):
        scope = _DOCSTRING_SCOPES.get(type(node))
        if scope is None:
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            blocks.append(_docstring_block(first.value, scope, text, lines))
    return blocks


def _docstring_block(node: ast.Constant, scope: Scope, text: str, lines: list[str]) -> CommentBlock:
    segment = ast.get_source_segment(text, node) or ""
    quote_idx = next(k for k, c in enumerate(segment) if c in "'\"")
    triple = segment[quote_idx : quote_idx + 3]
    quote = triple if triple in ('"""', "'''") else segment[quote_idx]
    marker = segment[:quote_idx] + quote  # e.g. "r" + '"""' for an r-string docstring

    end_line = node.end_lineno or node.lineno
    end_col_offset = node.end_col_offset if node.end_col_offset is not None else node.col_offset

    return CommentBlock(
        style="docstring",
        marker_prefix=marker,
        marker_suffix=quote,
        start_line=node.lineno,
        end_line=end_line,
        start_col=_byte_col_to_char_col(lines, node.lineno, node.col_offset),
        end_col=_byte_col_to_char_col(lines, end_line, end_col_offset),
        indent=_leading_whitespace(lines, node.lineno),
        trailing=False,
        text=node.value,
        scope=scope,
    )


def _byte_col_to_char_col(lines: list[str], line_no: int, byte_offset: int) -> int:
    """`ast` reports col_offset/end_col_offset as UTF-8 *byte* offsets, not
    character indices -- convert so they can be used to slice `lines` (plain
    Python strings). Off by a lot on any line with non-ASCII text before the
    offset, e.g. a Japanese docstring, which is the common case here."""
    if line_no - 1 >= len(lines):
        return byte_offset
    line = lines[line_no - 1]
    return len(line.encode("utf-8")[:byte_offset].decode("utf-8"))


def _is_translatable(block: CommentBlock) -> bool:
    if not any(ch.isalpha() for ch in block.text):
        return False
    if block.style == "line" and block.start_line == 1 and block.text.startswith("!"):
        return False  # shebang
    if block.style == "line" and block.start_line <= 2 and _ENCODING_DECL_RE.search(block.text):
        return False
    return True
