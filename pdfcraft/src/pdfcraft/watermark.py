from __future__ import annotations

import io
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

from pdfcraft.ranges import parse_page_ranges

_PAGE_NUMBER_MARGIN = 24.0
_PAGE_NUMBER_HEIGHT = 20.0

# (rect-builder, text-align) per position, rect-builder takes page.rect.
_POSITIONS = {
    "bottom-center": lambda r: (fitz.Rect(0, r.height - _PAGE_NUMBER_MARGIN, r.width, r.height - _PAGE_NUMBER_MARGIN + _PAGE_NUMBER_HEIGHT), fitz.TEXT_ALIGN_CENTER),
    "bottom-right": lambda r: (fitz.Rect(r.width - 150, r.height - _PAGE_NUMBER_MARGIN, r.width - 20, r.height - _PAGE_NUMBER_MARGIN + _PAGE_NUMBER_HEIGHT), fitz.TEXT_ALIGN_RIGHT),
    "bottom-left": lambda r: (fitz.Rect(20, r.height - _PAGE_NUMBER_MARGIN, 170, r.height - _PAGE_NUMBER_MARGIN + _PAGE_NUMBER_HEIGHT), fitz.TEXT_ALIGN_LEFT),
    "top-center": lambda r: (fitz.Rect(0, _PAGE_NUMBER_MARGIN - _PAGE_NUMBER_HEIGHT, r.width, _PAGE_NUMBER_MARGIN), fitz.TEXT_ALIGN_CENTER),
}


def add_text_watermark(
    input_path: Path,
    output_path: Path,
    text: str,
    opacity: float = 0.3,
    fontsize: float = 48,
    page_spec: str | None = None,
) -> Path:
    """Overlay diagonal watermark text on every page (or the pages in
    `page_spec`), faded to `opacity` (0-1) via PyMuPDF's real
    `fill_opacity` alpha blending. `insert_textbox`'s `rotate` only
    accepts multiples of 90, so the 45-degree tilt is done via a `morph`
    rotation matrix on `insert_text` instead, with the text's own width
    used to center it on the page before rotating."""
    if not 0.0 <= opacity <= 1.0:
        raise ValueError("opacity must be between 0.0 and 1.0")

    with fitz.open(input_path) as doc:
        pages = parse_page_ranges(page_spec, doc.page_count) if page_spec else range(doc.page_count)
        for p in pages:
            page = doc[p]
            center = fitz.Point(page.rect.width / 2, page.rect.height / 2)
            text_width = fitz.get_text_length(text, fontsize=fontsize)
            origin = fitz.Point(center.x - text_width / 2, center.y)
            page.insert_text(
                origin,
                text,
                fontsize=fontsize,
                color=(0, 0, 0),
                fill_opacity=opacity,
                morph=(center, fitz.Matrix(45)),
                overlay=True,
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path)
    return output_path


def add_image_watermark(
    input_path: Path,
    output_path: Path,
    image_path: Path,
    opacity: float = 0.3,
    page_spec: str | None = None,
) -> Path:
    """Overlay `image_path`, faded to `opacity` (0-1) via a real alpha
    channel, centered on every page (or the pages in `page_spec`)."""
    if not 0.0 <= opacity <= 1.0:
        raise ValueError("opacity must be between 0.0 and 1.0")

    with Image.open(image_path) as im:
        rgba = im.convert("RGBA")
        alpha = rgba.getchannel("A").point(lambda a: round(a * opacity))
        rgba.putalpha(alpha)
        buf = io.BytesIO()
        rgba.save(buf, format="PNG")
        faded_bytes = buf.getvalue()
        img_w, img_h = rgba.size

    with fitz.open(input_path) as doc:
        pages = parse_page_ranges(page_spec, doc.page_count) if page_spec else range(doc.page_count)
        for p in pages:
            page = doc[p]
            r = page.rect
            scale = min(r.width / img_w, r.height / img_h)
            fit_w, fit_h = img_w * scale, img_h * scale
            cx, cy = r.width / 2, r.height / 2
            rect = fitz.Rect(cx - fit_w / 2, cy - fit_h / 2, cx + fit_w / 2, cy + fit_h / 2)
            page.insert_image(rect, stream=faded_bytes, overlay=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path)
    return output_path


def add_page_numbers(
    input_path: Path,
    output_path: Path,
    fmt: str = "{n}/{total}",
    position: str = "bottom-center",
    fontsize: float = 10,
) -> Path:
    """Stamp a page number (default "N/total") into the footer of every
    page. `fmt` is a str.format() template with `n` (1-indexed) and
    `total`."""
    if position not in _POSITIONS:
        raise ValueError(f"unknown position '{position}' (expected one of {sorted(_POSITIONS)})")
    position_fn = _POSITIONS[position]

    with fitz.open(input_path) as doc:
        total = doc.page_count
        for n, page in enumerate(doc, start=1):
            rect, align = position_fn(page.rect)
            page.insert_textbox(
                rect, fmt.format(n=n, total=total), fontsize=fontsize, align=align, overlay=True
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path)
    return output_path
