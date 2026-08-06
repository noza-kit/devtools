from __future__ import annotations

import base64

from mailwatch.message import parse_message


def _b64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii")


def test_parse_message_multipart_with_attachment():
    raw = {
        "id": "msg1",
        "threadId": "thread1",
        "internalDate": "1704067200000",
        "snippet": "snippet text",
        "payload": {
            "mimeType": "multipart/mixed",
            "headers": [
                {"name": "From", "value": "Boss <boss@example.com>"},
                {"name": "Subject", "value": "至急: 請求書"},
                {"name": "Date", "value": "Mon, 1 Jan 2024 09:00:00 +0900"},
            ],
            "parts": [
                {
                    "mimeType": "multipart/alternative",
                    "parts": [
                        {
                            "mimeType": "text/plain",
                            "body": {"data": _b64url("本文プレーンテキスト")},
                        },
                        {
                            "mimeType": "text/html",
                            "body": {"data": _b64url("<p>本文HTML</p>")},
                        },
                    ],
                },
                {
                    "mimeType": "application/pdf",
                    "filename": "invoice.pdf",
                    "body": {"attachmentId": "att1", "size": 12345},
                },
            ],
        },
    }

    message = parse_message(raw)

    assert message.id == "msg1"
    assert message.from_header == "Boss <boss@example.com>"
    assert message.subject == "至急: 請求書"
    assert message.internal_date_ms == 1704067200000
    assert message.body_text == "本文プレーンテキスト"
    assert len(message.attachments) == 1
    assert message.attachments[0].filename == "invoice.pdf"
    assert message.attachments[0].attachment_id == "att1"


def test_parse_message_falls_back_to_html_when_no_plain_text():
    raw = {
        "id": "msg2",
        "internalDate": "0",
        "payload": {
            "mimeType": "text/html",
            "headers": [],
            "body": {"data": _b64url("<p>HTMLのみ</p>")},
        },
    }

    message = parse_message(raw)

    assert "HTMLのみ" in message.body_text
    assert "<p>" not in message.body_text


def test_parse_message_falls_back_to_snippet_when_no_body():
    raw = {
        "id": "msg3",
        "internalDate": "0",
        "snippet": "スニペットのみ",
        "payload": {"mimeType": "text/plain", "headers": []},
    }

    message = parse_message(raw)

    assert message.body_text == "スニペットのみ"
    assert message.attachments == []
