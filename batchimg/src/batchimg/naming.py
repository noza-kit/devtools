from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional


class RenameTemplateError(Exception):
    pass


def render_filename(
    source: Path,
    index: int,
    template: Optional[str],
    *,
    mtime: datetime,
    digits: int = 4,
    date_format: str = "%Y%m%d",
) -> str:
    """Render an output filename for `source`.

    With no template, the original filename is kept as-is. Otherwise `template`
    is formatted with {n} (zero-padded index), {date} (mtime, `date_format`),
    {stem} (original stem) and {ext} (original extension, no dot). If the
    rendered name has no extension of its own, the source's extension is
    appended automatically.
    """
    if template is None:
        return source.name

    fields = {
        "n": str(index).zfill(digits),
        "date": mtime.strftime(date_format),
        "stem": source.stem,
        "ext": source.suffix.lstrip(".").lower(),
    }
    try:
        name = template.format(**fields)
    except (KeyError, IndexError) as exc:
        raise RenameTemplateError(f"Unknown placeholder in rename template: {exc}") from exc

    if not Path(name).suffix:
        name += source.suffix.lower()
    return name
