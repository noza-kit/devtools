from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF
import yaml
from PIL import Image

from pdfcraft.pages import A4_HEIGHT, A4_WIDTH
from pdfcraft.ranges import parse_page_ranges

MARGIN = 36.0  # 0.5 inch, in points
TITLE_HEIGHT = 28.0
CAPTION_HEIGHT = 24.0
GRID_GAP = 12.0


def pdf_to_images(
    input_path: Path,
    output_dir: Path,
    page_spec: str | None = None,
    fmt: str = "png",
    dpi: int = 200,
) -> list[Path]:
    """Render pages to image files, one per page. `fmt` is "png" or
    "jpeg"; `page_spec` ("1-3,5") selects pages, default is all pages."""
    fmt = fmt.lower()
    if fmt not in ("png", "jpeg", "jpg"):
        raise ValueError(f"unsupported image format '{fmt}' (expected png/jpeg)")
    ext = "jpg" if fmt in ("jpeg", "jpg") else "png"

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    outputs: list[Path] = []

    with fitz.open(input_path) as doc:
        pages = parse_page_ranges(page_spec, doc.page_count) if page_spec else range(doc.page_count)
        digits = max(4, len(str(doc.page_count)))
        for p in pages:
            pix = doc[p].get_pixmap(matrix=matrix)
            out_path = output_dir / f"{stem}_page{p + 1:0{digits}d}.{ext}"
            pix.save(out_path)
            outputs.append(out_path)

    return outputs


@dataclass
class ReportEntry:
    path: Path
    title: str = ""
    caption: str = ""


def load_batch_config(config_path: Path) -> list[ReportEntry]:
    """Load a batch report config (CSV or YAML) into a list of
    ReportEntry. CSV columns: image_path (or path), title, caption
    (title/caption optional, extra columns ignored). YAML: a list of
    mappings with the same keys."""
    suffix = config_path.suffix.lower()
    entries: list[ReportEntry] = []
    base_dir = config_path.parent

    if suffix == ".csv":
        with open(config_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                raw_path = row.get("image_path") or row.get("path")
                if not raw_path:
                    raise ValueError("CSV row is missing an 'image_path'/'path' column")
                entries.append(_make_entry(raw_path, row.get("title", ""), row.get("caption", ""), base_dir))
    elif suffix in (".yaml", ".yml"):
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or []
        if not isinstance(data, list):
            raise ValueError("YAML batch config must be a list of entries")
        for row in data:
            raw_path = row.get("image_path") or row.get("path")
            if not raw_path:
                raise ValueError("YAML entry is missing an 'image_path'/'path' key")
            entries.append(_make_entry(raw_path, row.get("title", ""), row.get("caption", ""), base_dir))
    else:
        raise ValueError(f"unsupported batch config format '{suffix}' (expected .csv/.yaml/.yml)")

    if not entries:
        raise ValueError(f"batch config '{config_path}' contains no entries")
    return entries


def _make_entry(raw_path: str, title: str, caption: str, base_dir: Path) -> ReportEntry:
    path = Path(raw_path)
    if not path.is_absolute():
        path = base_dir / path
    return ReportEntry(path=path, title=title or "", caption=caption or "")


def images_to_pdf(
    image_paths: list[Path],
    output_path: Path,
    title: str | None = None,
    caption: str | None = None,
) -> Path:
    """Basic image-to-PDF: one image per page, centered and scaled to fit
    within the page margins, with an optional shared title/caption on
    every page."""
    entries = [ReportEntry(path=p, title=title or "", caption=caption or "") for p in image_paths]
    return build_report(entries, output_path, grid=1)


def build_report(entries: list[ReportEntry], output_path: Path, grid: int = 1) -> Path:
    """Render a title+caption report from `entries`. `grid` is images per
    page: 1 (one image, own title/caption per page) or 2/4 (a grid of
    images per page, each with its own caption underneath; page-level
    title is omitted for grid layouts since each cell has its own)."""
    if grid not in (1, 2, 4):
        raise ValueError("grid must be 1, 2, or 4")

    with fitz.open() as doc:
        if grid == 1:
            for entry in entries:
                _add_single_page(doc, entry)
        else:
            rows, cols = (1, 2) if grid == 2 else (2, 2)
            for i in range(0, len(entries), grid):
                _add_grid_page(doc, entries[i : i + grid], rows, cols)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path)
    return output_path


def _add_single_page(doc: "fitz.Document", entry: ReportEntry) -> None:
    page = doc.new_page(width=A4_WIDTH, height=A4_HEIGHT)
    top = MARGIN
    bottom = A4_HEIGHT - MARGIN

    if entry.title:
        page.insert_textbox(
            fitz.Rect(MARGIN, top, A4_WIDTH - MARGIN, top + TITLE_HEIGHT),
            entry.title,
            fontsize=16,
            align=fitz.TEXT_ALIGN_CENTER,
        )
        top += TITLE_HEIGHT

    if entry.caption:
        bottom -= CAPTION_HEIGHT
        page.insert_textbox(
            fitz.Rect(MARGIN, bottom, A4_WIDTH - MARGIN, bottom + CAPTION_HEIGHT),
            entry.caption,
            fontsize=11,
            align=fitz.TEXT_ALIGN_CENTER,
        )

    image_rect = fitz.Rect(MARGIN, top, A4_WIDTH - MARGIN, bottom)
    _insert_image_fit(page, image_rect, entry.path)


def _add_grid_page(doc: "fitz.Document", entries: list[ReportEntry], rows: int, cols: int) -> None:
    page = doc.new_page(width=A4_WIDTH, height=A4_HEIGHT)
    usable_w = A4_WIDTH - 2 * MARGIN
    usable_h = A4_HEIGHT - 2 * MARGIN
    cell_w = (usable_w - (cols - 1) * GRID_GAP) / cols
    cell_h = (usable_h - (rows - 1) * GRID_GAP) / rows

    for idx, entry in enumerate(entries):
        row, col = divmod(idx, cols)
        x0 = MARGIN + col * (cell_w + GRID_GAP)
        y0 = MARGIN + row * (cell_h + GRID_GAP)
        cell_bottom = y0 + cell_h

        if entry.caption:
            cell_bottom -= CAPTION_HEIGHT
            page.insert_textbox(
                fitz.Rect(x0, cell_bottom, x0 + cell_w, cell_bottom + CAPTION_HEIGHT),
                entry.caption,
                fontsize=9,
                align=fitz.TEXT_ALIGN_CENTER,
            )

        _insert_image_fit(page, fitz.Rect(x0, y0, x0 + cell_w, cell_bottom), entry.path)


def _insert_image_fit(page: "fitz.Page", rect: "fitz.Rect", image_path: Path) -> None:
    """Insert an image into `rect`, preserving aspect ratio and centering
    it within the rect (letterboxed, not stretched/cropped)."""
    with Image.open(image_path) as im:
        img_w, img_h = im.size
    if img_w <= 0 or img_h <= 0:
        raise ValueError(f"image '{image_path}' has invalid dimensions")

    scale = min(rect.width / img_w, rect.height / img_h)
    fit_w, fit_h = img_w * scale, img_h * scale
    cx, cy = rect.x0 + rect.width / 2, rect.y0 + rect.height / 2
    fit_rect = fitz.Rect(cx - fit_w / 2, cy - fit_h / 2, cx + fit_w / 2, cy + fit_h / 2)
    page.insert_image(fit_rect, filename=str(image_path))
