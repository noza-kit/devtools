from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import fitz  # PyMuPDF

# Heuristic thresholds. These are deliberately simple (see README's
# "known limitations" section) rather than a full layout-analysis model.
_HEADER_FOOTER_ZONE = 0.08  # top/bottom 8% of page height
_HEADER_FOOTER_MIN_PAGE_FRACTION = 0.5  # text must recur on >=50% of pages to count as a header/footer
_MIN_PAGES_FOR_HEADER_FOOTER_DETECTION = 3
_TOC_LINE_RE = re.compile(r".+\.{3,}\s*\d+\s*$")  # "Introduction ..... 12"
_ISOLATED_NUMBER_RE = re.compile(r"^[\d.,\-%\s]{1,6}$")

_BOLD_FLAG = 1 << 4


def extract_markdown(
    input_path: Path,
    skip_headers: bool = True,
    skip_footers: bool = True,
    skip_toc_lines: bool = True,
    skip_isolated_numbers: bool = True,
    skip_image_pages_pct: float | None = None,
    min_text_chars: int = 0,
) -> str:
    """Extract a structure-preserving Markdown document from a PDF.

    Heading level is inferred from font size relative to the document's
    most common ("body") font size. Recurring top/bottom-of-page text
    (headers/footers), dot-leader TOC lines, and short isolated numeric
    lines (chart axis labels etc.) are filtered out by default. Pages
    whose image coverage exceeds `skip_image_pages_pct`, or whose text
    is shorter than `min_text_chars`, are skipped entirely.
    """
    with fitz.open(input_path) as doc:
        pages_data = [_page_blocks(doc[p]) for p in range(doc.page_count)]
        body_size = _detect_body_size(pages_data)
        header_footer_texts = (
            _detect_recurring_edge_text(doc, pages_data)
            if (skip_headers or skip_footers) and doc.page_count >= _MIN_PAGES_FOR_HEADER_FOOTER_DETECTION
            else set()
        )

        lines: list[str] = []
        for pno, page in enumerate(doc):
            if skip_image_pages_pct is not None and _image_coverage_pct(page) >= skip_image_pages_pct:
                continue

            page_lines = _render_page_markdown(
                pages_data[pno],
                page.rect.height,
                body_size,
                header_footer_texts,
                skip_headers,
                skip_footers,
                skip_toc_lines,
                skip_isolated_numbers,
            )
            page_text = "\n".join(page_lines).strip()
            if len(page_text) < min_text_chars:
                continue
            if page_text:
                lines.append(page_text)

    return "\n\n".join(lines) + ("\n" if lines else "")


def _page_blocks(page: "fitz.Page") -> list[dict]:
    return [b for b in page.get_text("dict")["blocks"] if b.get("type") == 0]


def _detect_body_size(pages_data: list[list[dict]]) -> float:
    counts: Counter[float] = Counter()
    for blocks in pages_data:
        for block in blocks:
            for line in block["lines"]:
                for span in line["spans"]:
                    counts[round(span["size"], 1)] += len(span["text"])
    return counts.most_common(1)[0][0] if counts else 10.0


def _detect_recurring_edge_text(doc: "fitz.Document", pages_data: list[list[dict]]) -> set[str]:
    """Returns a set of *normalized* header/footer texts (digit runs
    collapsed to '#') that recur across enough pages. Normalizing first
    means a page-numbered footer like "Page 1" / "Page 2" / ... is still
    recognized as one recurring pattern rather than N distinct strings
    that each only appear once."""
    top_counts: Counter[str] = Counter()
    bottom_counts: Counter[str] = Counter()

    for pno, blocks in enumerate(pages_data):
        page_height = doc[pno].rect.height
        top_zone = page_height * _HEADER_FOOTER_ZONE
        bottom_zone = page_height * (1 - _HEADER_FOOTER_ZONE)
        for block in blocks:
            text = _block_text(block).strip()
            if not text:
                continue
            y0, y1 = block["bbox"][1], block["bbox"][3]
            if y1 <= top_zone:
                top_counts[_normalize_for_recurrence(text)] += 1
            elif y0 >= bottom_zone:
                bottom_counts[_normalize_for_recurrence(text)] += 1

    min_occurrences = max(2, round(len(pages_data) * _HEADER_FOOTER_MIN_PAGE_FRACTION))
    recurring = {t for t, c in top_counts.items() if c >= min_occurrences}
    recurring |= {t for t, c in bottom_counts.items() if c >= min_occurrences}
    return recurring


def _normalize_for_recurrence(text: str) -> str:
    return re.sub(r"\d+", "#", text)


def _block_text(block: dict) -> str:
    return "\n".join(
        "".join(span["text"] for span in line["spans"]) for line in block["lines"]
    )


def _image_coverage_pct(page: "fitz.Page") -> float:
    page_area = page.rect.width * page.rect.height
    if page_area <= 0:
        return 0.0
    covered = 0.0
    for xref in {img[0] for img in page.get_images(full=True)}:
        for rect in page.get_image_rects(xref):
            covered += rect.width * rect.height
    return min(100.0, 100.0 * covered / page_area)


def _render_page_markdown(
    blocks: list[dict],
    page_height: float,
    body_size: float,
    header_footer_texts: set[str],
    skip_headers: bool,
    skip_footers: bool,
    skip_toc_lines: bool,
    skip_isolated_numbers: bool,
) -> list[str]:
    heading_sizes = sorted(
        {round(span["size"], 1) for block in blocks for line in block["lines"] for span in line["spans"]
         if round(span["size"], 1) > body_size * 1.05},
        reverse=True,
    )
    top_zone = page_height * _HEADER_FOOTER_ZONE
    bottom_zone = page_height * (1 - _HEADER_FOOTER_ZONE)

    out: list[str] = []
    for block in blocks:
        text = _block_text(block).strip()
        if not text:
            continue

        y0, y1 = block["bbox"][1], block["bbox"][3]
        normalized = _normalize_for_recurrence(text)
        if skip_headers and y1 <= top_zone and normalized in header_footer_texts:
            continue
        if skip_footers and y0 >= bottom_zone and normalized in header_footer_texts:
            continue

        for line in block["lines"]:
            line_text = "".join(span["text"] for span in line["spans"]).strip()
            if not line_text:
                continue
            if skip_toc_lines and _TOC_LINE_RE.match(line_text):
                continue
            if skip_isolated_numbers and _ISOLATED_NUMBER_RE.match(line_text) and len(blocks) > 1:
                continue

            max_size = max((round(s["size"], 1) for s in line["spans"]), default=body_size)
            level = heading_sizes.index(max_size) + 1 if max_size in heading_sizes else 0
            if level:
                out.append(f"{'#' * min(level, 4)} {line_text}")
            else:
                out.append(line_text)
        out.append("")  # paragraph break between blocks

    return out
