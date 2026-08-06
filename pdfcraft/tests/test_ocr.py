"""OCR tests inject a fake OCREngine rather than exercising the real
EasyOCR backend: EasyOCR needs its optional [ocr] extra (torch et al.)
installed and downloads model weights on first use, which isn't
appropriate for a unit test. ocr_extract()'s page-selection, DPI
rendering, and language-code mapping are all exercised for real; only
image -> text recognition itself is faked. See README's "OCR" section
for how to manually verify the real EasyOCR path."""
from pathlib import Path

import pytest
from PIL import Image

from pdfcraft import ocr


class FakeEngine:
    def __init__(self):
        self.calls: list[tuple[tuple[int, int], list[str]]] = []

    def recognize(self, image: Image.Image, languages: list[str]) -> str:
        self.calls.append((image.size, languages))
        return f"[recognized {len(languages)} lang(s)]"


def test_ocr_extract_processes_all_pages_by_default(sample_pdf: Path):
    engine = FakeEngine()
    text = ocr.ocr_extract(sample_pdf, lang="eng", engine=engine)
    assert len(engine.calls) == 6
    assert text.count("[recognized") == 6


def test_ocr_extract_respects_page_spec(sample_pdf: Path):
    engine = FakeEngine()
    ocr.ocr_extract(sample_pdf, lang="eng", page_spec="1-2", engine=engine)
    assert len(engine.calls) == 2


def test_ocr_extract_maps_tesseract_style_lang_codes(sample_pdf: Path):
    engine = FakeEngine()
    ocr.ocr_extract(sample_pdf, lang="jpn+eng", page_spec="1", engine=engine)
    _, languages = engine.calls[0]
    assert languages == ["ja", "en"]


def test_ocr_extract_passes_through_unrecognized_lang_code(sample_pdf: Path):
    engine = FakeEngine()
    ocr.ocr_extract(sample_pdf, lang="es", page_spec="1", engine=engine)
    _, languages = engine.calls[0]
    assert languages == ["es"]


def test_easyocr_engine_raises_helpful_error_without_extra(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "easyocr":
            raise ImportError("No module named 'easyocr'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    engine = ocr.EasyOCREngine()
    with pytest.raises(ImportError, match=r"pdfcraft\[ocr\]"):
        engine.recognize(Image.new("RGB", (10, 10)), ["en"])
