from __future__ import annotations

from mailwatch.attachments import save_attachments
from mailwatch.message import Attachment, ParsedMessage


def test_save_attachments_writes_files(tmp_path, monkeypatch):
    calls = []

    def fake_get_attachment_data(access_token, message_id, attachment_id):
        calls.append((access_token, message_id, attachment_id))
        return b"file-bytes"

    monkeypatch.setattr("mailwatch.attachments.get_attachment_data", fake_get_attachment_data)

    message = ParsedMessage(
        id="msg1",
        thread_id="t1",
        from_header="a@example.com",
        subject="s",
        date_header="d",
        internal_date_ms=0,
        body_text="",
        attachments=[
            Attachment(filename="invoice.pdf", attachment_id="att1", mime_type="application/pdf", size=10),
        ],
    )

    saved = save_attachments("token", message, tmp_path / "out")

    assert len(saved) == 1
    assert saved[0].read_bytes() == b"file-bytes"
    assert saved[0].name == "msg1_invoice.pdf"
    assert calls == [("token", "msg1", "att1")]


def test_save_attachments_sanitizes_unsafe_filename(tmp_path, monkeypatch):
    monkeypatch.setattr("mailwatch.attachments.get_attachment_data", lambda *a, **k: b"x")

    message = ParsedMessage(
        id="msg1",
        thread_id="t1",
        from_header="a@example.com",
        subject="s",
        date_header="d",
        internal_date_ms=0,
        body_text="",
        attachments=[
            Attachment(filename="weird:/name?.txt", attachment_id="att1", mime_type="text/plain", size=1),
        ],
    )

    saved = save_attachments("token", message, tmp_path / "out")

    assert "/" not in saved[0].name.replace(f"msg1_", "")
    assert ":" not in saved[0].name
    assert "?" not in saved[0].name
