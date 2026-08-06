from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from notesearch import scanner
from notesearch.chunking import Chunk, chunk_text
from notesearch.config import Settings

logger = logging.getLogger("notesearch")


class IndexStore(Protocol):
    def get_indexed_sources(self) -> dict[str, float]: ...
    def upsert_document(self, source: str, chunks: list[Chunk], mtime: float) -> None: ...
    def delete_document(self, source: str) -> None: ...


@dataclass(frozen=True)
class SyncReport:
    added: int = 0
    updated: int = 0
    unchanged: int = 0

    @property
    def changed(self) -> int:
        return self.added + self.updated


@dataclass(frozen=True)
class CleanReport:
    removed: int = 0


def sync_index(store: IndexStore, settings: Settings) -> SyncReport:
    """The JIT sync used by every search: compare each eligible file's
    mtime against what's already indexed, and (re-)embed only what's
    new or changed. Reading `store.get_indexed_sources()` and diffing
    is what makes repeated searches fast -- an unchanged file costs one
    dict lookup, not a re-embed."""
    pdf_mds = scanner.convert_pdfs(settings.target_dirs, settings.exclude) if settings.auto_convert_pdf else []
    files = list(dict.fromkeys(scanner.scan_files(settings.target_dirs, settings.exclude, settings.extensions) + pdf_mds))

    indexed = store.get_indexed_sources()
    added = updated = unchanged = 0

    for path in files:
        source = str(path)
        mtime = path.stat().st_mtime
        indexed_mtime = indexed.get(source)

        if indexed_mtime is None:
            added += 1
        elif indexed_mtime < mtime:
            updated += 1
        else:
            unchanged += 1
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            logger.exception("could not read %s, skipping", path)
            continue

        chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
        store.upsert_document(source, chunks, mtime)

    return SyncReport(added=added, updated=updated, unchanged=unchanged)


def clean_index(store: IndexStore) -> CleanReport:
    """Purges chunks belonging to files that no longer exist on disk
    (deleted or renamed since they were last indexed)."""
    removed = 0
    for source in store.get_indexed_sources():
        if not Path(source).exists():
            store.delete_document(source)
            removed += 1
    return CleanReport(removed=removed)
