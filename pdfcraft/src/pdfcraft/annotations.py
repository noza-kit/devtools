from __future__ import annotations

from pathlib import Path
from typing import TypedDict

import fitz  # PyMuPDF


class AnnotationInfo(TypedDict):
    page: int  # 1-indexed
    type: str
    content: str
    author: str
    rect: tuple[float, float, float, float]


def extract_annotations(input_path: Path) -> list[AnnotationInfo]:
    """Extract highlights, comments/notes, and other markup annotations
    from a PDF, in page then on-page order."""
    results: list[AnnotationInfo] = []
    with fitz.open(input_path) as doc:
        for pno, page in enumerate(doc):
            for annot in page.annots() or []:
                info = annot.info
                results.append(
                    {
                        "page": pno + 1,
                        "type": annot.type[1],
                        "content": info.get("content", ""),
                        "author": info.get("title", ""),
                        "rect": tuple(annot.rect),
                    }
                )
    return results
