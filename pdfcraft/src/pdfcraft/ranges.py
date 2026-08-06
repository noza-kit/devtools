from __future__ import annotations


class PageRangeError(ValueError):
    """Raised for a malformed or out-of-bounds page range spec."""


def parse_page_ranges(spec: str, total_pages: int) -> list[int]:
    """Parse a 1-indexed, comma-separated page range spec ("1-3,5,8-10")
    into a sorted, de-duplicated list of 0-indexed page numbers.

    Ranges are inclusive on both ends. Whitespace around commas/dashes is
    ignored. Raises PageRangeError for empty specs, non-numeric tokens,
    an inverted range (e.g. "5-2"), or any page number outside
    [1, total_pages].
    """
    spec = spec.strip()
    if not spec:
        raise PageRangeError("page range spec is empty")

    pages: set[int] = set()
    for token in spec.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            start_s, _, end_s = token.partition("-")
            start, end = _parse_int(start_s, token), _parse_int(end_s, token)
            if start > end:
                raise PageRangeError(f"invalid range '{token}': start > end")
            for p in range(start, end + 1):
                pages.add(_check_bounds(p, total_pages, token))
        else:
            p = _parse_int(token, token)
            pages.add(_check_bounds(p, total_pages, token))

    if not pages:
        raise PageRangeError("page range spec produced no pages")
    return sorted(p - 1 for p in pages)


def _parse_int(text: str, token: str) -> int:
    text = text.strip()
    if not text.isdigit():
        raise PageRangeError(f"invalid page number in '{token}'")
    return int(text)


def _check_bounds(page: int, total_pages: int, token: str) -> int:
    if page < 1 or page > total_pages:
        raise PageRangeError(
            f"page {page} in '{token}' is out of bounds (document has {total_pages} pages)"
        )
    return page


def format_page_ranges(pages: list[int]) -> str:
    """Inverse of parse_page_ranges: 0-indexed page numbers -> a compact
    1-indexed "1-3,5,8-10" spec string. Input need not be sorted."""
    if not pages:
        return ""
    ordered = sorted(set(p + 1 for p in pages))
    groups: list[str] = []
    start = prev = ordered[0]
    for p in ordered[1:]:
        if p == prev + 1:
            prev = p
            continue
        groups.append(str(start) if start == prev else f"{start}-{prev}")
        start = prev = p
    groups.append(str(start) if start == prev else f"{start}-{prev}")
    return ",".join(groups)
