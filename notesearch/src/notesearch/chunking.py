from __future__ import annotations

import re
from dataclasses import dataclass

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")

DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50


@dataclass(frozen=True)
class Chunk:
    text: str
    heading: str  # the nearest enclosing "# Heading" text; "" if the chunk precedes any heading
    start_line: int = 1  # 1-indexed line in the source file this chunk begins at, for editor jump-to-line


def split_by_headings(text: str) -> list[tuple[str, str, int]]:
    """First-stage split: cut on Markdown '#'..'######' headings into
    (heading_text, section_body, body_start_line) triples. Content
    before the first heading (or the whole file, if it has none at
    all) gets heading "". Empty sections are dropped."""
    lines = text.splitlines()
    sections: list[tuple[str, str, int]] = []
    heading = ""
    body_lines: list[str] = []
    body_start = 1

    def flush() -> None:
        body = "\n".join(body_lines).strip()
        if body:
            sections.append((heading, body, body_start))

    for i, line in enumerate(lines, start=1):
        m = _HEADING_RE.match(line)
        if m:
            flush()
            heading = m.group(2).strip()
            body_lines = []
            body_start = i + 1
        else:
            if not body_lines:
                body_start = i
            body_lines.append(line)

    flush()
    return sections


def fixed_size_chunks(
    text: str, start_line: int = 1, size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP
) -> list[tuple[str, int]]:
    """Fallback split for a section (or a whole heading-less file) that's
    still too long: fixed-width windows with `overlap` characters of
    context repeated between consecutive chunks. Returns (piece,
    approximate_start_line) pairs -- the line number is derived by
    counting newlines before each piece's start offset."""
    if len(text) <= size:
        return [(text, start_line)]
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")

    pieces = []
    start = 0
    while start < len(text):
        end = start + size
        piece_start_line = start_line + text[:start].count("\n")
        pieces.append((text[start:end], piece_start_line))
        if end >= len(text):
            break
        start = end - overlap
    return pieces


def chunk_text(text: str, size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> list[Chunk]:
    """The hybrid chunking strategy: heading-based sections first, each
    of which is further cut with fixed_size_chunks() only if it's still
    longer than `size`."""
    sections = split_by_headings(text)
    if not sections:
        # split_by_headings returns [] only when every section's body is
        # empty -- either the whole input is blank, or (edge case) it's
        # nothing but a heading line with no body text under it at all
        # (e.g. text == "# Empty Heading"). Either way, fall back to
        # treating the raw (stripped) text as one heading-less chunk.
        stripped = text.strip()
        sections = [("", stripped, 1)] if stripped else []

    chunks: list[Chunk] = []
    for heading, body, body_start in sections:
        for piece, line in fixed_size_chunks(body, body_start, size, overlap):
            chunks.append(Chunk(text=piece, heading=heading, start_line=line))
    return chunks
