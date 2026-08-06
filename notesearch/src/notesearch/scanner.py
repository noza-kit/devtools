from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("notesearch")


def scan_files(target_dirs: list[Path], exclude: list[str], extensions: list[str]) -> list[Path]:
    """Every file under `target_dirs` (recursively) whose suffix is in
    `extensions`, skipping any path with a component matching
    `exclude` (e.g. "venv", ".git") anywhere along it. A `target_dirs`
    entry that doesn't exist is silently skipped, not an error (a
    stale/typo'd config entry shouldn't crash every search)."""
    extensions_lower = {e.lower() for e in extensions}
    exclude_set = set(exclude)
    results: list[Path] = []

    for root in target_dirs:
        if not root.exists():
            logger.warning("target_dirs entry does not exist, skipping: %s", root)
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in extensions_lower:
                continue
            if exclude_set & set(path.relative_to(root).parts):
                continue
            results.append(path)

    return results


def convert_pdfs(target_dirs: list[Path], exclude: list[str]) -> list[Path]:
    """Convert every .pdf under `target_dirs` to a sibling .md (via
    pdfcraft, if it's installed) and return the paths of the resulting
    .md files, skipping any PDF whose .md is already newer. Returns []
    immediately, without raising, if pdfcraft isn't installed -- PDF
    auto-conversion is opt-in (see Settings.auto_convert_pdf) and
    silently unavailable rather than a hard dependency."""
    try:
        from pdfcraft.extract_md import extract_markdown
    except ImportError:
        logger.warning("pdfcraft is not installed; skipping PDF auto-conversion")
        return []

    exclude_set = set(exclude)
    converted: list[Path] = []

    for root in target_dirs:
        if not root.exists():
            continue
        for pdf_path in root.rglob("*.pdf"):
            if exclude_set & set(pdf_path.relative_to(root).parts):
                continue
            md_path = pdf_path.with_suffix(".md")
            if md_path.exists() and md_path.stat().st_mtime >= pdf_path.stat().st_mtime:
                converted.append(md_path)
                continue
            try:
                md_path.write_text(extract_markdown(pdf_path), encoding="utf-8")
                converted.append(md_path)
            except Exception:
                logger.exception("pdfcraft conversion failed for %s", pdf_path)

    return converted
