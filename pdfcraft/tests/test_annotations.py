from pathlib import Path

from pdfcraft import annotations


def test_extracts_highlight_with_content_and_author(sample_pdf: Path):
    results = annotations.extract_annotations(sample_pdf)
    assert len(results) == 1
    assert results[0]["content"] == "要確認"
    assert results[0]["author"] == "reviewer"
    assert results[0]["page"] == 3
    assert results[0]["type"] == "Highlight"


def test_no_annotations_returns_empty_list(tmp_path: Path):
    import fitz

    doc = fitz.open()
    doc.new_page()
    path = tmp_path / "plain.pdf"
    doc.save(path)
    doc.close()
    assert annotations.extract_annotations(path) == []
