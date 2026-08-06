from pathlib import Path

import fitz
import pytest

from pdfcraft import security


def test_encrypt_requires_password_to_open(sample_pdf: Path, tmp_path: Path):
    out = security.encrypt(sample_pdf, tmp_path / "enc.pdf", "secret123")
    with fitz.open(out) as d:
        assert d.needs_pass
        assert d.authenticate("secret123")


def test_decrypt_removes_password(sample_pdf: Path, tmp_path: Path):
    enc = security.encrypt(sample_pdf, tmp_path / "enc.pdf", "secret123")
    dec = security.decrypt(enc, tmp_path / "dec.pdf", "secret123")
    with fitz.open(dec) as d:
        assert not d.needs_pass


def test_decrypt_wrong_password_raises(sample_pdf: Path, tmp_path: Path):
    enc = security.encrypt(sample_pdf, tmp_path / "enc.pdf", "secret123")
    with pytest.raises(ValueError):
        security.decrypt(enc, tmp_path / "dec.pdf", "wrongpassword")


def test_sanitize_metadata_clears_fields(sample_pdf: Path, tmp_path: Path):
    with fitz.open(sample_pdf) as d:
        d.set_metadata({"author": "Alex", "title": "Secret"})
        withmeta = tmp_path / "withmeta.pdf"
        d.save(withmeta)

    out = security.sanitize_metadata(withmeta, tmp_path / "sanitized.pdf")
    with fitz.open(out) as d:
        assert d.metadata["author"] == ""
        assert d.metadata["title"] == ""


def test_redact_keywords_removes_text(sample_pdf: Path, tmp_path: Path):
    out = security.redact(sample_pdf, tmp_path / "redacted.pdf", keywords=["山田太郎"])
    with fitz.open(out) as d:
        assert "山田太郎" not in d[2].get_text()


def test_redact_pattern_removes_matching_tokens(sample_pdf: Path, tmp_path: Path):
    out = security.redact(sample_pdf, tmp_path / "redacted.pdf", pattern=r"[A-Z]{2}-\d{4}")
    with fitz.open(out) as d:
        assert "AB-9999" not in d[2].get_text()


def test_redact_box_removes_content_in_region(sample_pdf: Path, tmp_path: Path):
    out = security.redact(sample_pdf, tmp_path / "redacted.pdf", boxes=[(0, (50, 70, 545, 115))])
    with fitz.open(out) as d:
        assert "Chapter 1" not in d[0].get_text()


def test_redact_leaves_other_pages_untouched(sample_pdf: Path, tmp_path: Path):
    out = security.redact(sample_pdf, tmp_path / "redacted.pdf", keywords=["山田太郎"])
    with fitz.open(out) as d:
        assert "Chapter 1" in d[0].get_text()


def test_redact_requires_at_least_one_target(sample_pdf: Path, tmp_path: Path):
    with pytest.raises(ValueError):
        security.redact(sample_pdf, tmp_path / "out.pdf")
