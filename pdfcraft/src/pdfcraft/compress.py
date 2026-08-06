from __future__ import annotations

from pathlib import Path
from typing import Literal

import fitz  # PyMuPDF

Quality = Literal["high", "medium", "low"]

# (target DPI, JPEG quality) per level, via PyMuPDF's Document.rewrite_images.
# dpi_threshold must be strictly greater than dpi_target (PyMuPDF requirement);
# a small margin above the target means images already near-at-target are left
# untouched (no upscaling, no needless re-encode of images that wouldn't shrink).
_QUALITY_SETTINGS: dict[Quality, tuple[int, int]] = {
    "high": (200, 85),
    "medium": (150, 70),
    "low": (100, 50),
}
_DPI_THRESHOLD_MARGIN = 20


def compress(input_path: Path, output_path: Path, quality: Quality = "medium") -> Path:
    """Recompress a PDF's embedded images (DPI downsampling + JPEG
    re-encode) and run structural cleanup (duplicate-object removal,
    stream deflation) on save."""
    if quality not in _QUALITY_SETTINGS:
        raise ValueError(f"unknown quality level '{quality}' (expected high/medium/low)")
    dpi_target, jpeg_quality = _QUALITY_SETTINGS[quality]

    with fitz.open(input_path) as doc:
        doc.rewrite_images(
            dpi_threshold=dpi_target + _DPI_THRESHOLD_MARGIN, dpi_target=dpi_target, quality=jpeg_quality
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path, garbage=4, deflate=True)
    return output_path
