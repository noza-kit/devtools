from __future__ import annotations

from pathlib import Path

import fitz
import pytest


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """A 6-page PDF: 5 content pages (recurring header "Sample Document",
    a "Page N" footer, an H1-sized heading, and body text) + 1 blank
    page. Page 3 additionally has a red image, a line of PII-like text
    ("090-1234-5678 / AB-9999 / 山田太郎"), and a highlight annotation."""
    doc = fitz.open()
    for i in range(1, 6):
        page = doc.new_page(width=595, height=842)
        page.insert_textbox(fitz.Rect(0, 20, 595, 40), "Sample Document", fontsize=9, align=fitz.TEXT_ALIGN_CENTER)
        page.insert_textbox(fitz.Rect(0, 800, 595, 820), f"Page {i}", fontsize=8, align=fitz.TEXT_ALIGN_CENTER)
        page.insert_textbox(fitz.Rect(50, 70, 545, 115), f"Chapter {i}: Introduction", fontsize=20)
        page.insert_textbox(fitz.Rect(50, 130, 545, 300), "This is some body text. " * 20, fontsize=11)
        if i == 3:
            pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 300, 200))
            pix.set_rect(pix.irect, (255, 0, 0))
            page.insert_image(fitz.Rect(100, 400, 400, 550), pixmap=pix)
            page.insert_textbox(fitz.Rect(50, 560, 545, 580), "090-1234-5678 / AB-9999 / 山田太郎に連絡", fontsize=11)
            annot = page.add_highlight_annot(fitz.Rect(50, 130, 545, 150))
            annot.set_info(content="要確認", title="reviewer")
            annot.update()
    doc.new_page(width=595, height=842)  # trailing blank page

    path = tmp_path / "sample.pdf"
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    from PIL import Image

    path = tmp_path / "logo.png"
    Image.new("RGBA", (120, 80), (0, 0, 255, 255)).save(path)
    return path
