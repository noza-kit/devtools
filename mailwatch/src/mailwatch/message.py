from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field

_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class Attachment:
    filename: str
    attachment_id: str
    mime_type: str
    size: int


@dataclass
class ParsedMessage:
    id: str
    thread_id: str
    from_header: str
    subject: str
    date_header: str
    internal_date_ms: int
    body_text: str
    attachments: list[Attachment] = field(default_factory=list)


def _header(headers: list[dict], name: str) -> str:
    name = name.lower()
    for h in headers:
        if h.get("name", "").lower() == name:
            return h.get("value", "")
    return ""


def _decode_part_data(data_b64url: str) -> str:
    raw = base64.urlsafe_b64decode(data_b64url + "=" * (-len(data_b64url) % 4))
    return raw.decode("utf-8", errors="replace")


def _strip_html(html: str) -> str:
    return _TAG_RE.sub(" ", html)


def _walk_parts(payload: dict, texts: dict[str, list[str]], attachments: list[Attachment]) -> None:
    mime_type = payload.get("mimeType", "")
    filename = payload.get("filename") or ""
    body = payload.get("body") or {}

    if filename and body.get("attachmentId"):
        attachments.append(
            Attachment(
                filename=filename,
                attachment_id=body["attachmentId"],
                mime_type=mime_type,
                size=body.get("size", 0),
            )
        )
    elif mime_type in ("text/plain", "text/html") and body.get("data"):
        texts.setdefault(mime_type, []).append(_decode_part_data(body["data"]))

    for part in payload.get("parts") or []:
        _walk_parts(part, texts, attachments)


def parse_message(raw: dict) -> ParsedMessage:
    """Turn a Gmail `messages.get(format=full)` response into a flat, matchable shape.

    Prefers the text/plain body for keyword matching; falls back to a
    tag-stripped text/html body, then the API-provided snippet, for
    messages with no plain-text part.
    """
    payload = raw.get("payload") or {}
    headers = payload.get("headers") or []
    texts: dict[str, list[str]] = {}
    attachments: list[Attachment] = []
    _walk_parts(payload, texts, attachments)

    if texts.get("text/plain"):
        body_text = "\n".join(texts["text/plain"])
    elif texts.get("text/html"):
        body_text = _strip_html("\n".join(texts["text/html"]))
    else:
        body_text = raw.get("snippet", "")

    return ParsedMessage(
        id=raw["id"],
        thread_id=raw.get("threadId", ""),
        from_header=_header(headers, "From"),
        subject=_header(headers, "Subject"),
        date_header=_header(headers, "Date"),
        internal_date_ms=int(raw.get("internalDate", 0)),
        body_text=body_text,
        attachments=attachments,
    )
