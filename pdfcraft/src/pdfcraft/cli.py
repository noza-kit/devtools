from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from pdfcraft import annotations as annotations_mod
from pdfcraft import compress as compress_mod
from pdfcraft import convert
from pdfcraft import extract_md as extract_md_mod
from pdfcraft import ocr as ocr_mod
from pdfcraft import pages
from pdfcraft import security
from pdfcraft import watermark as watermark_mod
from pdfcraft.ranges import PageRangeError

app = typer.Typer(help="Local-only PDF toolkit: pages, compression, security, and layout-aware extraction.")
console = Console()
err_console = Console(stderr=True)


def _fail(message: str) -> None:
    err_console.print(f"[red]エラー: {message}[/red]")
    raise typer.Exit(code=1)


def _human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} GB"


# --- Module A: page operations ------------------------------------------------


@app.command()
def split(
    input: Path,
    ranges: Optional[List[str]] = typer.Option(None, "--ranges", help="Repeatable; each occurrence becomes one output file, e.g. --ranges 1-3 --ranges 5,8-10. Omit to split one file per page."),
    output_dir: Path = typer.Option(Path("."), "--output-dir", "-o"),
) -> None:
    """Split a PDF into multiple files."""
    try:
        outputs = pages.split(input, output_dir, ranges)
    except (PageRangeError, ValueError, RuntimeError) as e:
        _fail(str(e))
    console.print(f"[green]{len(outputs)}個のファイルに分割しました[/green] -> {output_dir}")
    for p in outputs:
        console.print(f"  {p.name}")


@app.command()
def merge(
    inputs: List[Path],
    output: Path = typer.Option(..., "-o", "--output"),
    toc: bool = typer.Option(True, "--toc/--no-toc", help="Add a bookmark per source file"),
    page_numbers: bool = typer.Option(False, "--page-numbers", help="Stamp N/total page numbers on the merged result"),
) -> None:
    """Merge PDFs in the given order."""
    try:
        if page_numbers:
            # PyMuPDF refuses a non-incremental save back to the same path
            # a document was opened from, so page-numbering happens via a
            # temp file rather than merge -> output -> re-save(output).
            with tempfile.TemporaryDirectory() as tmp:
                merged = Path(tmp) / "merged.pdf"
                pages.merge(inputs, merged, toc=toc)
                watermark_mod.add_page_numbers(merged, output)
        else:
            pages.merge(inputs, output, toc=toc)
    except (ValueError, RuntimeError) as e:
        _fail(str(e))
    console.print(f"[green]{len(inputs)}個のファイルを統合しました[/green] -> {output}")


@app.command()
def extract(
    input: Path,
    pages_spec: str = typer.Option(..., "--pages", help='e.g. "1-3,5"'),
    output: Path = typer.Option(..., "-o", "--output"),
) -> None:
    """Keep only the given pages."""
    try:
        pages.extract(input, output, pages_spec)
    except PageRangeError as e:
        _fail(str(e))
    console.print(f"[green]抽出しました[/green] -> {output}")


@app.command()
def delete(
    input: Path,
    pages_spec: str = typer.Option(..., "--pages", help='e.g. "1-3,5"'),
    output: Path = typer.Option(..., "-o", "--output"),
) -> None:
    """Remove the given pages, keeping the rest."""
    try:
        pages.delete(input, output, pages_spec)
    except (PageRangeError, ValueError) as e:
        _fail(str(e))
    console.print(f"[green]削除しました[/green] -> {output}")


@app.command("remove-blank")
def remove_blank(input: Path, output: Path = typer.Option(..., "-o", "--output")) -> None:
    """Auto-detect and drop blank pages."""
    try:
        _, removed = pages.remove_blank_pages(input, output)
    except ValueError as e:
        _fail(str(e))
    console.print(f"[green]{removed}ページの白紙ページを削除しました[/green] -> {output}")


@app.command()
def rotate(
    input: Path,
    degrees: int = typer.Option(..., help="90/180/270 (added to existing rotation)"),
    pages_spec: Optional[str] = typer.Option(None, "--pages", help="Default: all pages"),
    output: Path = typer.Option(..., "-o", "--output"),
) -> None:
    """Rotate pages."""
    try:
        pages.rotate(input, output, degrees, pages_spec)
    except (PageRangeError, ValueError) as e:
        _fail(str(e))
    console.print(f"[green]回転しました[/green] -> {output}")


@app.command()
def nup(
    input: Path,
    n: int = typer.Option(2, help="2 or 4 pages per output page"),
    output: Path = typer.Option(..., "-o", "--output"),
) -> None:
    """N-up: lay out N source pages per output page."""
    try:
        pages.n_up(input, output, n)
    except ValueError as e:
        _fail(str(e))
    console.print(f"[green]{n}-up で面付けしました[/green] -> {output}")


# --- Module B: image <-> PDF ---------------------------------------------------


@app.command("pdf-to-img")
def pdf_to_img(
    input: Path,
    output_dir: Path = typer.Option(Path("."), "-o", "--output-dir"),
    pages_spec: Optional[str] = typer.Option(None, "--pages"),
    format: str = typer.Option("png", "--format"),
    dpi: int = typer.Option(200, "--dpi"),
) -> None:
    """Render pages to image files."""
    try:
        outputs = convert.pdf_to_images(input, output_dir, pages_spec, format, dpi)
    except (PageRangeError, ValueError) as e:
        _fail(str(e))
    console.print(f"[green]{len(outputs)}枚の画像を書き出しました[/green] -> {output_dir}")


@app.command("img-to-pdf")
def img_to_pdf(
    inputs: List[Path],
    output: Path = typer.Option(..., "-o", "--output"),
    title: Optional[str] = typer.Option(None, "--title"),
    caption: Optional[str] = typer.Option(None, "--caption"),
) -> None:
    """Convert one or more images into a single PDF (one image per page)."""
    try:
        convert.images_to_pdf(inputs, output, title, caption)
    except ValueError as e:
        _fail(str(e))
    console.print(f"[green]PDFを生成しました[/green] -> {output}")


@app.command()
def report(
    config: Path = typer.Option(..., "--config", help="CSV or YAML: image_path, title, caption columns/keys"),
    output: Path = typer.Option(..., "-o", "--output"),
    grid: int = typer.Option(1, "--grid", help="Images per page: 1, 2, or 4"),
) -> None:
    """Batch-generate a titled/captioned PDF report from a CSV/YAML list of images."""
    try:
        entries = convert.load_batch_config(config)
        convert.build_report(entries, output, grid=grid)
    except (ValueError, FileNotFoundError) as e:
        _fail(str(e))
    console.print(f"[green]{len(entries)}枚の画像からレポートを生成しました[/green] -> {output}")


# --- Module C: security --------------------------------------------------------


@app.command()
def encrypt(
    input: Path,
    output: Path = typer.Option(..., "-o", "--output"),
    user_password: str = typer.Option(..., "--user-password", prompt=True, hide_input=True),
    owner_password: Optional[str] = typer.Option(None, "--owner-password"),
    allow_modification: bool = typer.Option(False, "--allow-modification"),
) -> None:
    """Password-protect a PDF (AES-256)."""
    security.encrypt(input, output, user_password, owner_password, allow_modification=allow_modification)
    console.print(f"[green]暗号化しました[/green] -> {output}")


@app.command()
def decrypt(
    input: Path,
    output: Path = typer.Option(..., "-o", "--output"),
    password: str = typer.Option(..., prompt=True, hide_input=True),
) -> None:
    """Remove password protection from a PDF."""
    try:
        security.decrypt(input, output, password)
    except ValueError as e:
        _fail(str(e))
    console.print(f"[green]復号しました[/green] -> {output}")


@app.command()
def sanitize(input: Path, output: Path = typer.Option(..., "-o", "--output")) -> None:
    """Strip metadata (author, creator, dates, embedded XML metadata, ...)."""
    security.sanitize_metadata(input, output)
    console.print(f"[green]メタデータを削除しました[/green] -> {output}")


@app.command()
def redact(
    input: Path,
    output: Path = typer.Option(..., "-o", "--output"),
    keywords: Optional[List[str]] = typer.Option(None, "--keywords"),
    pattern: Optional[str] = typer.Option(None, "--pattern"),
    box: Optional[List[str]] = typer.Option(None, "--box", help='"x0,y0,x1,y1", repeatable'),
    page: int = typer.Option(1, "--page", help="1-indexed page that --box coordinates apply to"),
) -> None:
    """Permanently black out keywords/regex matches/coordinate boxes."""
    boxes = None
    if box:
        try:
            boxes = [(page - 1, tuple(float(v) for v in b.split(","))) for b in box]
        except ValueError:
            _fail('--box must be "x0,y0,x1,y1"')
    try:
        security.redact(input, output, keywords, pattern, boxes)
    except ValueError as e:
        _fail(str(e))
    console.print(f"[green]墨消ししました[/green] -> {output}")


# --- Module D: extraction & decoration -----------------------------------------


@app.command("extract-md")
def extract_md_cmd(
    input: Path,
    output: Path = typer.Option(..., "-o", "--output"),
    skip_headers: bool = typer.Option(True, "--skip-headers/--no-skip-headers"),
    skip_footers: bool = typer.Option(True, "--skip-footers/--no-skip-footers"),
    skip_toc: bool = typer.Option(True, "--skip-toc/--no-skip-toc"),
    skip_image_pages: Optional[float] = typer.Option(None, "--skip-image-pages", help="Skip pages whose image coverage is >= this percent"),
    min_text_chars: int = typer.Option(0, "--min-text-chars"),
) -> None:
    """Extract structured, noise-filtered Markdown."""
    text = extract_md_mod.extract_markdown(
        input, skip_headers, skip_footers, skip_toc, True, skip_image_pages, min_text_chars
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    console.print(f"[green]Markdownを抽出しました[/green] -> {output}")


@app.command()
def ocr(
    input: Path,
    output: Path = typer.Option(..., "-o", "--output"),
    lang: str = typer.Option("eng", "--lang", help='Tesseract-style codes, e.g. "jpn+eng"'),
    pages_spec: Optional[str] = typer.Option(None, "--pages"),
) -> None:
    """OCR a scanned PDF to plain text."""
    try:
        text = ocr_mod.ocr_extract(input, lang, pages_spec)
    except (PageRangeError, ImportError) as e:
        _fail(str(e))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    console.print(f"[green]OCR抽出しました[/green] -> {output}")


@app.command()
def annotations(input: Path, output: Optional[Path] = typer.Option(None, "-o", "--output", help="Write JSON; omit to print a table")) -> None:
    """Extract highlights/comments/notes."""
    results = annotations_mod.extract_annotations(input)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"[green]{len(results)}件の注釈を抽出しました[/green] -> {output}")
        return

    table = Table("page", "type", "author", "content")
    for a in results:
        table.add_row(str(a["page"]), a["type"], a["author"], a["content"])
    console.print(table)


@app.command()
def watermark(
    input: Path,
    output: Path = typer.Option(..., "-o", "--output"),
    text: Optional[str] = typer.Option(None, "--text"),
    image: Optional[Path] = typer.Option(None, "--image"),
    opacity: float = typer.Option(0.3, "--opacity"),
) -> None:
    """Add a diagonal text or centered image watermark."""
    if not text and not image:
        _fail("--text か --image のどちらかを指定してください")
    try:
        if text:
            watermark_mod.add_text_watermark(input, output, text, opacity)
        else:
            watermark_mod.add_image_watermark(input, output, image, opacity)
    except ValueError as e:
        _fail(str(e))
    console.print(f"[green]透かしを追加しました[/green] -> {output}")


@app.command("page-numbers")
def page_numbers_cmd(
    input: Path,
    output: Path = typer.Option(..., "-o", "--output"),
    format: str = typer.Option("{n}/{total}", "--format"),
    position: str = typer.Option("bottom-center", "--position"),
) -> None:
    """Stamp page numbers into the footer of every page."""
    try:
        watermark_mod.add_page_numbers(input, output, format, position)
    except ValueError as e:
        _fail(str(e))
    console.print(f"[green]ページ番号を付与しました[/green] -> {output}")


@app.command()
def compress(
    input: Path,
    output: Path = typer.Option(..., "-o", "--output"),
    quality: str = typer.Option("medium", "--quality", help="high/medium/low"),
) -> None:
    """Shrink file size by recompressing embedded images."""
    before = input.stat().st_size
    try:
        compress_mod.compress(input, output, quality)
    except ValueError as e:
        _fail(str(e))
    after = output.stat().st_size
    saved_pct = 100 * (1 - after / before) if before else 0
    console.print(
        f"[green]圧縮しました[/green] -> {output} "
        f"({_human_size(before)} -> {_human_size(after)}, {saved_pct:.0f}%削減)"
    )
