from pathlib import Path

import fitz
import pytest

from pdfcraft import pages
from pdfcraft.ranges import PageRangeError


def test_split_by_ranges(sample_pdf: Path, tmp_path: Path):
    outputs = pages.split(sample_pdf, tmp_path / "out", ["1-2", "3,5"])
    assert len(outputs) == 2
    with fitz.open(outputs[0]) as d:
        assert d.page_count == 2
    with fitz.open(outputs[1]) as d:
        assert d.page_count == 2


def test_split_per_page(sample_pdf: Path, tmp_path: Path):
    outputs = pages.split(sample_pdf, tmp_path / "out")
    assert len(outputs) == 6
    for o in outputs:
        with fitz.open(o) as d:
            assert d.page_count == 1


def test_merge_preserves_order_and_page_count(sample_pdf: Path, tmp_path: Path):
    out = pages.merge([sample_pdf, sample_pdf], tmp_path / "merged.pdf")
    with fitz.open(out) as d:
        assert d.page_count == 12


def test_merge_adds_toc_bookmark_per_file(sample_pdf: Path, tmp_path: Path):
    out = pages.merge([sample_pdf, sample_pdf], tmp_path / "merged.pdf", toc=True)
    with fitz.open(out) as d:
        toc = d.get_toc()
        assert len(toc) == 2
        assert toc[0][2] == 1
        assert toc[1][2] == 7


def test_merge_without_toc(sample_pdf: Path, tmp_path: Path):
    out = pages.merge([sample_pdf, sample_pdf], tmp_path / "merged.pdf", toc=False)
    with fitz.open(out) as d:
        assert d.get_toc() == []


def test_extract_keeps_only_given_pages(sample_pdf: Path, tmp_path: Path):
    out = pages.extract(sample_pdf, tmp_path / "extracted.pdf", "1-2")
    with fitz.open(out) as d:
        assert d.page_count == 2


def test_extract_invalid_range_raises(sample_pdf: Path, tmp_path: Path):
    with pytest.raises(PageRangeError):
        pages.extract(sample_pdf, tmp_path / "out.pdf", "1-99")


def test_delete_removes_given_pages(sample_pdf: Path, tmp_path: Path):
    out = pages.delete(sample_pdf, tmp_path / "deleted.pdf", "6")
    with fitz.open(out) as d:
        assert d.page_count == 5


def test_delete_all_pages_raises(sample_pdf: Path, tmp_path: Path):
    with pytest.raises(ValueError):
        pages.delete(sample_pdf, tmp_path / "out.pdf", "1-6")


def test_remove_blank_pages_drops_trailing_blank(sample_pdf: Path, tmp_path: Path):
    out, removed = pages.remove_blank_pages(sample_pdf, tmp_path / "noblank.pdf")
    assert removed == 1
    with fitz.open(out) as d:
        assert d.page_count == 5


def test_remove_blank_pages_all_blank_raises(tmp_path: Path):
    doc = fitz.open()
    doc.new_page()
    doc.new_page()
    src = tmp_path / "allblank.pdf"
    doc.save(src)
    doc.close()
    with pytest.raises(ValueError):
        pages.remove_blank_pages(src, tmp_path / "out.pdf")


def test_rotate_all_pages(sample_pdf: Path, tmp_path: Path):
    out = pages.rotate(sample_pdf, tmp_path / "rotated.pdf", 90)
    with fitz.open(out) as d:
        assert all(d[i].rotation == 90 for i in range(d.page_count))


def test_rotate_specific_pages(sample_pdf: Path, tmp_path: Path):
    out = pages.rotate(sample_pdf, tmp_path / "rotated.pdf", 180, page_spec="1")
    with fitz.open(out) as d:
        assert d[0].rotation == 180
        assert d[1].rotation == 0


def test_rotate_non_multiple_of_90_raises(sample_pdf: Path, tmp_path: Path):
    with pytest.raises(ValueError):
        pages.rotate(sample_pdf, tmp_path / "out.pdf", 45)


def test_n_up_2(sample_pdf: Path, tmp_path: Path):
    out = pages.n_up(sample_pdf, tmp_path / "nup2.pdf", 2)
    with fitz.open(out) as d:
        assert d.page_count == 3  # 6 source pages / 2 per output page


def test_n_up_4(sample_pdf: Path, tmp_path: Path):
    out = pages.n_up(sample_pdf, tmp_path / "nup4.pdf", 4)
    with fitz.open(out) as d:
        assert d.page_count == 2  # ceil(6 / 4)


def test_n_up_invalid_n_raises(sample_pdf: Path, tmp_path: Path):
    with pytest.raises(ValueError):
        pages.n_up(sample_pdf, tmp_path / "out.pdf", 3)


def test_is_blank_page_true_for_trailing_page(sample_pdf: Path):
    with fitz.open(sample_pdf) as d:
        assert pages.is_blank_page(d[5]) is True
        assert pages.is_blank_page(d[0]) is False
