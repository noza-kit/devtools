from pathlib import Path

import fitz
import pytest

from pdfcraft import compress


def test_compress_shrinks_file_size(sample_pdf: Path, tmp_path: Path):
    out = compress.compress(sample_pdf, tmp_path / "compressed.pdf", "low")
    assert out.stat().st_size < sample_pdf.stat().st_size


def test_compress_preserves_page_count(sample_pdf: Path, tmp_path: Path):
    out = compress.compress(sample_pdf, tmp_path / "compressed.pdf", "medium")
    with fitz.open(sample_pdf) as before, fitz.open(out) as after:
        assert before.page_count == after.page_count


@pytest.mark.parametrize("quality", ["high", "medium", "low"])
def test_compress_accepts_all_quality_levels(sample_pdf: Path, tmp_path: Path, quality: str):
    out = compress.compress(sample_pdf, tmp_path / f"c_{quality}.pdf", quality)
    assert out.exists()


def test_compress_invalid_quality_raises(sample_pdf: Path, tmp_path: Path):
    with pytest.raises(ValueError):
        compress.compress(sample_pdf, tmp_path / "out.pdf", "ultra")
