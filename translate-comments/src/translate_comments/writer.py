from __future__ import annotations

from pathlib import Path

from translate_comments.extractor import CommentBlock


def separate_output_path(source_path: str | Path, target_lang: str) -> Path:
    """`file.py` + "en" -> `file_en.py`, alongside the original."""
    source_path = Path(source_path)
    return source_path.with_name(f"{source_path.stem}_{target_lang}{source_path.suffix}")


def render_inline(
    text: str,
    blocks: list[CommentBlock],
    translations: dict[str, list[str]],
    target_langs: list[str],
) -> str:
    """Return `text` with a translated comment appended directly below each
    block, for each language in `target_langs`, in that order. Original code
    and comments are never modified -- only new lines are inserted.

    `translations[lang][i]` must be the translation of `blocks[i].text` into
    `lang`. A block's own comment marker is reused for the inserted
    translation, except for a docstring (style "docstring"): since only the
    first bare string-literal statement in a scope is semantically "the"
    docstring, a translated copy is added as a `#` comment instead of a
    second string-literal statement.
    """
    lines = text.splitlines(keepends=True)
    insertions: dict[int, list[str]] = {}

    for i, block in enumerate(blocks):
        rendered: list[str] = []
        for lang in target_langs:
            rendered.extend(_render_inline_lines(block, lang, translations[lang][i]))
        insertions.setdefault(block.end_line, []).extend(rendered)

    out: list[str] = []
    for line_no, line in enumerate(lines, start=1):
        if line_no in insertions and not line.endswith("\n"):
            line = line + "\n"  # ensure the line we're inserting after is terminated
        out.append(line)
        if line_no in insertions:
            ending = "\r\n" if line.endswith("\r\n") else "\n"
            out.extend(extra + ending for extra in insertions[line_no])

    return "".join(out)


def render_separate(text: str, blocks: list[CommentBlock], translations: list[str]) -> str:
    """Return a copy of `text` with each block's comment/docstring text
    replaced in place by its translation (`translations[i]` <-> `blocks[i]`).
    Code, and everything outside the extracted blocks, is untouched.
    """
    lines = text.splitlines(keepends=True)

    # Replace bottom-up: a replacement can change the line count, which would
    # invalidate not-yet-processed blocks' line numbers if we went top-down.
    for block, translated in sorted(zip(blocks, translations), key=lambda pair: -pair[0].start_line):
        lines = _replace_block(lines, block, translated)

    return "".join(lines)


def _render_inline_lines(block: CommentBlock, lang: str, translated: str) -> list[str]:
    tag = f"[{lang.upper()}] "
    parts = translated.split("\n")

    if block.style == "block":
        tagged = [f"{tag}{parts[0]}", *parts[1:]]
        if len(tagged) == 1:
            return [f"{block.indent}{block.marker_prefix} {tagged[0]} {block.marker_suffix}"]
        return [
            f"{block.indent}{block.marker_prefix}",
            *(f"{block.indent} {p}" for p in tagged),
            f"{block.indent}{block.marker_suffix}",
        ]

    marker = "#" if block.style == "docstring" else block.marker_prefix
    return [f"{block.indent}{marker} {tag if idx == 0 else ''}{p}" for idx, p in enumerate(parts)]


def _replace_block(lines: list[str], block: CommentBlock, translated: str) -> list[str]:
    start_idx = block.start_line - 1
    end_idx = block.end_line - 1

    prefix = lines[start_idx][: block.start_col]
    suffix = lines[end_idx][block.end_col :]

    replacement = prefix + _render_replacement(block, translated) + suffix
    return lines[:start_idx] + [replacement] + lines[end_idx + 1 :]


def _render_replacement(block: CommentBlock, translated: str) -> str:
    if block.style == "docstring":
        return f"{block.marker_prefix}{translated}{block.marker_suffix}"

    parts = translated.split("\n")

    if block.style == "block":
        if len(parts) == 1:
            return f"{block.marker_prefix} {parts[0]} {block.marker_suffix}"
        body = "".join(f"\n{block.indent} {p}" for p in parts)
        return f"{block.marker_prefix}{body}\n{block.indent}{block.marker_suffix}"

    first = f"{block.marker_prefix} {parts[0]}"
    rest = "".join(f"\n{block.indent}{block.marker_prefix} {p}" for p in parts[1:])
    return first + rest
