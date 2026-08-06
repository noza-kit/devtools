from __future__ import annotations

import re
from pathlib import Path

import fitz  # PyMuPDF

REDACT_FILL = (0, 0, 0)  # black box, matching the spec's "黒塗り"

_METADATA_FIELDS = (
    "title",
    "author",
    "subject",
    "keywords",
    "creator",
    "producer",
    "creationDate",
    "modDate",
    "trapped",
)


def encrypt(
    input_path: Path,
    output_path: Path,
    user_password: str,
    owner_password: str | None = None,
    allow_printing: bool = True,
    allow_copying: bool = True,
    allow_modification: bool = False,
) -> Path:
    """Encrypt a PDF with AES-256. `user_password` is required to open it
    at all; `owner_password` (defaults to `user_password` if omitted)
    additionally controls the permission bits."""
    permissions = 0
    if allow_printing:
        permissions |= fitz.PDF_PERM_PRINT
    if allow_copying:
        permissions |= fitz.PDF_PERM_COPY
    if allow_modification:
        permissions |= fitz.PDF_PERM_MODIFY | fitz.PDF_PERM_ANNOTATE

    with fitz.open(input_path) as doc:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(
            output_path,
            encryption=fitz.PDF_ENCRYPT_AES_256,
            user_pw=user_password,
            owner_pw=owner_password or user_password,
            permissions=permissions,
        )
    return output_path


def decrypt(input_path: Path, output_path: Path, password: str) -> Path:
    """Remove password protection from a PDF, given a password that can
    open it (user or owner password)."""
    with fitz.open(input_path) as doc:
        if doc.needs_pass:
            if not doc.authenticate(password):
                raise ValueError("incorrect password")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path, encryption=fitz.PDF_ENCRYPT_NONE)
    return output_path


def sanitize_metadata(input_path: Path, output_path: Path) -> Path:
    """Strip standard metadata fields (author, creator, producer, dates,
    ...) and any embedded XML metadata stream."""
    with fitz.open(input_path) as doc:
        doc.set_metadata({field: "" for field in _METADATA_FIELDS})
        try:
            doc.del_xml_metadata()
        except AttributeError:
            pass  # older PyMuPDF without XML metadata support; standard fields are still cleared
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path, garbage=4)
    return output_path


def redact(
    input_path: Path,
    output_path: Path,
    keywords: list[str] | None = None,
    pattern: str | None = None,
    boxes: list[tuple[int, tuple[float, float, float, float]]] | None = None,
    pages: list[int] | None = None,
) -> Path:
    """Permanently remove (black out, both visually and at the text/data
    level) any combination of: literal `keywords`, a regex `pattern`
    (matched per word — spanning-whitespace patterns won't match), and/or
    explicit `boxes` as (0-indexed page, (x0, y0, x1, y1)) tuples.
    `pages` restricts keyword/pattern search to those 0-indexed pages
    (default: all pages); `boxes` always carry their own page.
    """
    if not keywords and not pattern and not boxes:
        raise ValueError("redact requires at least one of keywords/pattern/boxes")

    compiled = re.compile(pattern) if pattern else None

    with fitz.open(input_path) as doc:
        target_pages = pages if pages is not None else range(doc.page_count)

        for p in target_pages:
            page = doc[p]
            if keywords:
                for kw in keywords:
                    for rect in page.search_for(kw):
                        page.add_redact_annot(rect, fill=REDACT_FILL)
            if compiled:
                for x0, y0, x1, y1, word, *_ in page.get_text("words"):
                    if compiled.search(word):
                        page.add_redact_annot(fitz.Rect(x0, y0, x1, y1), fill=REDACT_FILL)
            page.apply_redactions()

        if boxes:
            pages_touched: set[int] = set()
            for p, (x0, y0, x1, y1) in boxes:
                doc[p].add_redact_annot(fitz.Rect(x0, y0, x1, y1), fill=REDACT_FILL)
                pages_touched.add(p)
            for p in pages_touched:
                doc[p].apply_redactions()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path, garbage=4)
    return output_path
