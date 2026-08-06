from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

from pdfcraft.ranges import parse_page_ranges

# A4 in points (1 pt = 1/72 inch).
A4_WIDTH, A4_HEIGHT = 595.0, 842.0


def split(input_path: Path, output_dir: Path, ranges: list[str] | None = None) -> list[Path]:
    """Split a PDF into multiple files.

    If `ranges` is given, each entry ("1-3", "5,8-10", ...) becomes one
    output file containing exactly those pages, named
    "<stem>_partNN.pdf". If `ranges` is None, splits one file per page
    instead, named "<stem>_pageNNNN.pdf".
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem
    outputs: list[Path] = []

    with fitz.open(input_path) as doc:
        total = doc.page_count

        if ranges:
            for i, spec in enumerate(ranges, start=1):
                pages = parse_page_ranges(spec, total)
                out_path = output_dir / f"{stem}_part{i:02d}.pdf"
                with fitz.open() as new_doc:
                    for p in pages:
                        new_doc.insert_pdf(doc, from_page=p, to_page=p)
                    new_doc.save(out_path)
                outputs.append(out_path)
        else:
            digits = max(4, len(str(total)))
            for p in range(total):
                out_path = output_dir / f"{stem}_page{p + 1:0{digits}d}.pdf"
                with fitz.open() as new_doc:
                    new_doc.insert_pdf(doc, from_page=p, to_page=p)
                    new_doc.save(out_path)
                outputs.append(out_path)

    return outputs


def merge(input_paths: list[Path], output_path: Path, toc: bool = True) -> Path:
    """Merge PDFs in the given order into one file. When `toc` is true, a
    top-level bookmark (named after each source file's stem) is added
    pointing at the first page it contributed."""
    with fitz.open() as new_doc:
        toc_entries: list[list] = []
        page_cursor = 1  # 1-indexed, for fitz's set_toc

        for path in input_paths:
            with fitz.open(path) as src:
                if toc:
                    toc_entries.append([1, path.stem, page_cursor])
                new_doc.insert_pdf(src)
                page_cursor += src.page_count

        if toc and toc_entries:
            new_doc.set_toc(toc_entries)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        new_doc.save(output_path)

    return output_path


def extract(input_path: Path, output_path: Path, page_spec: str) -> Path:
    """Keep only the pages matching `page_spec` ("1-3,5"), in that order."""
    with fitz.open(input_path) as doc:
        pages = parse_page_ranges(page_spec, doc.page_count)
        doc.select(pages)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path)
    return output_path


def delete(input_path: Path, output_path: Path, page_spec: str) -> Path:
    """Remove the pages matching `page_spec`, keeping everything else in
    its original order."""
    with fitz.open(input_path) as doc:
        to_remove = set(parse_page_ranges(page_spec, doc.page_count))
        keep = [p for p in range(doc.page_count) if p not in to_remove]
        if not keep:
            raise ValueError("deleting these pages would leave an empty document")
        doc.select(keep)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path)
    return output_path


def is_blank_page(page: "fitz.Page", text_threshold: int = 0) -> bool:
    """Heuristic: a page counts as blank if it has no images and its
    extracted text (stripped) has at most `text_threshold` characters."""
    if page.get_images(full=True):
        return False
    text = page.get_text("text").strip()
    return len(text) <= text_threshold


def remove_blank_pages(input_path: Path, output_path: Path) -> tuple[Path, int]:
    """Drop pages detected as blank (see is_blank_page). Returns the
    output path and the number of pages removed."""
    with fitz.open(input_path) as doc:
        keep = [p for p in range(doc.page_count) if not is_blank_page(doc[p])]
        removed = doc.page_count - len(keep)
        if not keep:
            raise ValueError("every page was detected as blank; refusing to write an empty document")
        doc.select(keep)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path)
    return output_path, removed


def rotate(input_path: Path, output_path: Path, degrees: int, page_spec: str | None = None) -> Path:
    """Rotate pages by `degrees` (must be a multiple of 90), added to each
    page's existing rotation. `page_spec` selects which pages; None means
    all pages."""
    if degrees % 90 != 0:
        raise ValueError("degrees must be a multiple of 90")

    with fitz.open(input_path) as doc:
        pages = (
            parse_page_ranges(page_spec, doc.page_count)
            if page_spec
            else range(doc.page_count)
        )
        for p in pages:
            page = doc[p]
            page.set_rotation((page.rotation + degrees) % 360)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path)
    return output_path


def n_up(input_path: Path, output_path: Path, n: int = 2, page_size: tuple[float, float] = (A4_WIDTH, A4_HEIGHT)) -> Path:
    """Lay out `n` (2 or 4) source pages per output page, for handout
    printing. Pages are placed left-to-right, top-to-bottom in a grid
    sized to fit `n` (2 -> 1x2, 4 -> 2x2)."""
    if n not in (2, 4):
        raise ValueError("n_up only supports n=2 or n=4")

    rows, cols = (1, 2) if n == 2 else (2, 2)
    width, height = page_size
    cell_w, cell_h = width / cols, height / rows

    with fitz.open(input_path) as doc, fitz.open() as new_doc:
        total = doc.page_count
        for group_start in range(0, total, n):
            group = list(range(group_start, min(group_start + n, total)))
            new_page = new_doc.new_page(width=width, height=height)
            for idx, src_pno in enumerate(group):
                row, col = divmod(idx, cols)
                rect = fitz.Rect(
                    col * cell_w, row * cell_h, (col + 1) * cell_w, (row + 1) * cell_h
                )
                new_page.show_pdf_page(rect, doc, src_pno)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        new_doc.save(output_path)
    return output_path
