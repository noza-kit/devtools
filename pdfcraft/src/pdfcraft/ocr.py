from __future__ import annotations

from pathlib import Path
from typing import Protocol

import fitz  # PyMuPDF
from PIL import Image

from pdfcraft.ranges import parse_page_ranges

# Tesseract-style language codes (as used by the `--lang jpn+eng` CLI
# flag) mapped to EasyOCR's codes. Unrecognized codes are passed through
# unchanged, so an EasyOCR-native code also works directly.
_TESS_TO_EASYOCR = {"jpn": "ja", "eng": "en", "fra": "fr", "chi_sim": "ch_sim", "chi_tra": "ch_tra", "kor": "ko"}


class OCREngine(Protocol):
    """Swappable OCR backend. EasyOCREngine is the only implementation
    for now (pip-installable, no external binary); a TesseractOCREngine
    can be added later behind the same interface without touching
    ocr_extract() or the CLI."""

    def recognize(self, image: Image.Image, languages: list[str]) -> str: ...


class EasyOCREngine:
    """OCR via https://github.com/JaidedAI/EasyOCR. Readers are cached
    per language-set, since constructing one loads model weights."""

    def __init__(self) -> None:
        self._readers: dict[tuple[str, ...], object] = {}

    def recognize(self, image: Image.Image, languages: list[str]) -> str:
        try:
            import easyocr
            import numpy as np
        except ImportError as exc:
            raise ImportError(
                "OCR requires the 'ocr' extra: pip install \"pdfcraft[ocr]\""
            ) from exc

        key = tuple(sorted(languages))
        reader = self._readers.get(key)
        if reader is None:
            reader = easyocr.Reader(list(languages), gpu=False)
            self._readers[key] = reader

        array = np.array(image.convert("RGB"))
        lines: list[str] = reader.readtext(array, detail=0, paragraph=True)
        return "\n".join(lines)


def ocr_extract(
    input_path: Path,
    lang: str = "eng",
    page_spec: str | None = None,
    dpi: int = 200,
    engine: OCREngine | None = None,
) -> str:
    """OCR a (typically scanned/image-only) PDF. `lang` is a Tesseract-
    style '+'-joined code list ("jpn+eng"); `page_spec` ("1-3,5")
    restricts which pages are processed (default: all)."""
    engine = engine or EasyOCREngine()
    languages = [_TESS_TO_EASYOCR.get(code, code) for code in lang.split("+")]

    with fitz.open(input_path) as doc:
        pages = parse_page_ranges(page_spec, doc.page_count) if page_spec else range(doc.page_count)
        matrix = fitz.Matrix(dpi / 72, dpi / 72)
        texts: list[str] = []
        for p in pages:
            pix = doc[p].get_pixmap(matrix=matrix)
            mode = "RGB" if pix.n >= 3 else "L"
            image = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
            texts.append(engine.recognize(image, languages))

    return "\n\n".join(texts)
