from pathlib import Path

from pdfcraft import extract_md


def test_extracts_heading_and_body(sample_pdf: Path):
    md = extract_md.extract_markdown(sample_pdf)
    assert "# Chapter 1: Introduction" in md
    assert "This is some body text." in md


def test_filters_recurring_header(sample_pdf: Path):
    md = extract_md.extract_markdown(sample_pdf)
    assert "Sample Document" not in md


def test_filters_recurring_footer_with_changing_page_number(sample_pdf: Path):
    md = extract_md.extract_markdown(sample_pdf)
    assert "Page 1" not in md
    assert "Page 2" not in md


def test_no_skip_headers_keeps_header(sample_pdf: Path):
    md = extract_md.extract_markdown(sample_pdf, skip_headers=False, skip_footers=False)
    assert "Sample Document" in md


def test_skip_image_pages_drops_high_image_coverage_page(sample_pdf: Path):
    # Page 3 (index 2) has a large red image covering a meaningful fraction of the page.
    md_with_skip = extract_md.extract_markdown(sample_pdf, skip_image_pages_pct=1.0)
    md_without_skip = extract_md.extract_markdown(sample_pdf, skip_image_pages_pct=None)
    assert len(md_with_skip) < len(md_without_skip)


def test_min_text_chars_drops_short_pages(sample_pdf: Path):
    md = extract_md.extract_markdown(sample_pdf, min_text_chars=100_000)
    assert md == ""


def test_all_headings_use_consistent_level_for_same_size(sample_pdf: Path):
    md = extract_md.extract_markdown(sample_pdf)
    heading_lines = [line for line in md.splitlines() if line.startswith("# ")]
    assert len(heading_lines) == 5  # one per content page
