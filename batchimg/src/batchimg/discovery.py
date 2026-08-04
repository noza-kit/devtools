from __future__ import annotations

from pathlib import Path
from typing import Optional

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

DEFAULT_PATTERNS = [f"*{ext}" for ext in sorted(IMAGE_EXTENSIONS | VIDEO_EXTENSIONS)]


def classify(path: Path) -> Optional[str]:
    """Return "image", "video", or None for an unsupported extension."""
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    return None


def find_files(source_dir: Path, patterns: Optional[list[str]] = None, recursive: bool = False) -> list[Path]:
    """Find files under `source_dir` matching `patterns` (default: image + video extensions)."""
    patterns = patterns or DEFAULT_PATTERNS
    glob = source_dir.rglob if recursive else source_dir.glob
    files = sorted({f for pat in patterns for f in glob(pat) if f.is_file()})
    return files
