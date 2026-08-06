from pathlib import Path

import fitz
import pytest

from pdfcraft import watermark


def test_add_text_watermark_appears_on_every_page(sample_pdf: Path, tmp_path: Path):
    out = watermark.add_text_watermark(sample_pdf, tmp_path / "wm.pdf", "DRAFT", opacity=0.5)
    with fitz.open(sample_pdf) as before, fitz.open(out) as after:
        assert before.page_count == after.page_count
    assert out.exists() and out.stat().st_size > 0


def test_add_text_watermark_page_spec_limits_pages(sample_pdf: Path, tmp_path: Path):
    out = watermark.add_text_watermark(sample_pdf, tmp_path / "wm_one.pdf", "DRAFTMARK", page_spec="1")
    with fitz.open(out) as d:
        assert "DRAFTMARK" in d[0].get_text()
        assert "DRAFTMARK" not in d[1].get_text()


def test_add_text_watermark_invalid_opacity_raises(sample_pdf: Path, tmp_path: Path):
    with pytest.raises(ValueError):
        watermark.add_text_watermark(sample_pdf, tmp_path / "out.pdf", "DRAFT", opacity=1.5)


def test_add_image_watermark(sample_pdf: Path, sample_image: Path, tmp_path: Path):
    out = watermark.add_image_watermark(sample_pdf, tmp_path / "wm_img.pdf", sample_image, opacity=0.4)
    with fitz.open(sample_pdf) as before, fitz.open(out) as after:
        assert before.page_count == after.page_count


def test_add_image_watermark_invalid_opacity_raises(sample_pdf: Path, sample_image: Path, tmp_path: Path):
    with pytest.raises(ValueError):
        watermark.add_image_watermark(sample_pdf, tmp_path / "out.pdf", sample_image, opacity=-0.1)


def test_add_page_numbers_default_format(sample_pdf: Path, tmp_path: Path):
    out = watermark.add_page_numbers(sample_pdf, tmp_path / "numbered.pdf")
    with fitz.open(out) as d:
        assert "1/6" in d[0].get_text()
        assert "6/6" in d[5].get_text()


def test_add_page_numbers_custom_format(sample_pdf: Path, tmp_path: Path):
    out = watermark.add_page_numbers(sample_pdf, tmp_path / "numbered.pdf", fmt="Page {n} of {total}")
    with fitz.open(out) as d:
        assert "Page 1 of 6" in d[0].get_text()


def test_add_page_numbers_invalid_position_raises(sample_pdf: Path, tmp_path: Path):
    with pytest.raises(ValueError):
        watermark.add_page_numbers(sample_pdf, tmp_path / "out.pdf", position="middle")
