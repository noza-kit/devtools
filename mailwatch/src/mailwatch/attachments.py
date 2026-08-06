from __future__ import annotations

import re
from pathlib import Path

from mailwatch.gmail_client import get_attachment_data
from mailwatch.message import ParsedMessage

_UNSAFE_CHARS = re.compile(r'[\\/:*?"<>|]')


def _safe_filename(name: str) -> str:
    name = _UNSAFE_CHARS.sub("_", name).strip()
    return name or "attachment"


def save_attachments(access_token: str, message: ParsedMessage, save_dir: Path) -> list[Path]:
    """Download every attachment on `message` into `save_dir`, prefixed with
    the message id so re-running never collides across different emails."""
    save_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for att in message.attachments:
        data = get_attachment_data(access_token, message.id, att.attachment_id)
        out_path = save_dir / f"{message.id}_{_safe_filename(att.filename)}"
        out_path.write_bytes(data)
        saved.append(out_path)
    return saved
