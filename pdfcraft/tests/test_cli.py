from __future__ import annotations

import json
from pathlib import Path

import fitz
from typer.testing import CliRunner

from pdfcraft.cli import app

runner = CliRunner()


def test_split_command(sample_pdf: Path, tmp_path: Path):
    result = runner.invoke(app, ["split", str(sample_pdf), "--ranges", "1-2", "-o", str(tmp_path / "out")])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "out" / f"{sample_pdf.stem}_part01.pdf").exists()


def test_merge_command(sample_pdf: Path, tmp_path: Path):
    out = tmp_path / "merged.pdf"
    result = runner.invoke(app, ["merge", str(sample_pdf), str(sample_pdf), "-o", str(out)])
    assert result.exit_code == 0, result.output
    with fitz.open(out) as d:
        assert d.page_count == 12


def test_merge_command_with_page_numbers(sample_pdf: Path, tmp_path: Path):
    out = tmp_path / "merged.pdf"
    result = runner.invoke(app, ["merge", str(sample_pdf), str(sample_pdf), "-o", str(out), "--page-numbers"])
    assert result.exit_code == 0, result.output
    with fitz.open(out) as d:
        assert "1/12" in d[0].get_text()


def test_extract_command_invalid_range_fails_cleanly(sample_pdf: Path, tmp_path: Path):
    result = runner.invoke(app, ["extract", str(sample_pdf), "--pages", "1-99", "-o", str(tmp_path / "out.pdf")])
    assert result.exit_code == 1
    assert "エラー" in result.output


def test_compress_command_reports_size_reduction(sample_pdf: Path, tmp_path: Path):
    out = tmp_path / "compressed.pdf"
    result = runner.invoke(app, ["compress", str(sample_pdf), "-o", str(out), "--quality", "low"])
    assert result.exit_code == 0, result.output
    assert "%削減" in result.output


def test_pdf_to_img_command(sample_pdf: Path, tmp_path: Path):
    out_dir = tmp_path / "imgs"
    result = runner.invoke(app, ["pdf-to-img", str(sample_pdf), "-o", str(out_dir), "--pages", "1-2", "--dpi", "72"])
    assert result.exit_code == 0, result.output
    assert len(list(out_dir.glob("*.png"))) == 2


def test_report_command(tmp_path: Path):
    from PIL import Image
    import yaml

    img_path = tmp_path / "a.png"
    Image.new("RGB", (100, 100), (255, 0, 0)).save(img_path)
    cfg = tmp_path / "batch.yaml"
    cfg.write_text(yaml.safe_dump([{"path": str(img_path), "title": "A"}]), encoding="utf-8")
    out = tmp_path / "report.pdf"

    result = runner.invoke(app, ["report", "--config", str(cfg), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_encrypt_and_decrypt_commands(sample_pdf: Path, tmp_path: Path):
    enc = tmp_path / "enc.pdf"
    result = runner.invoke(app, ["encrypt", str(sample_pdf), "-o", str(enc), "--user-password", "secret"])
    assert result.exit_code == 0, result.output

    dec = tmp_path / "dec.pdf"
    result = runner.invoke(app, ["decrypt", str(enc), "-o", str(dec), "--password", "secret"])
    assert result.exit_code == 0, result.output
    with fitz.open(dec) as d:
        assert not d.needs_pass


def test_redact_command_with_keywords(sample_pdf: Path, tmp_path: Path):
    out = tmp_path / "redacted.pdf"
    result = runner.invoke(app, ["redact", str(sample_pdf), "-o", str(out), "--keywords", "山田太郎"])
    assert result.exit_code == 0, result.output
    with fitz.open(out) as d:
        assert "山田太郎" not in d[2].get_text()


def test_redact_command_with_box(sample_pdf: Path, tmp_path: Path):
    out = tmp_path / "redacted.pdf"
    result = runner.invoke(
        app, ["redact", str(sample_pdf), "-o", str(out), "--box", "50,70,545,115", "--page", "1"]
    )
    assert result.exit_code == 0, result.output
    with fitz.open(out) as d:
        assert "Chapter 1" not in d[0].get_text()


def test_redact_command_no_target_fails(sample_pdf: Path, tmp_path: Path):
    result = runner.invoke(app, ["redact", str(sample_pdf), "-o", str(tmp_path / "out.pdf")])
    assert result.exit_code == 1


def test_extract_md_command(sample_pdf: Path, tmp_path: Path):
    out = tmp_path / "out.md"
    result = runner.invoke(app, ["extract-md", str(sample_pdf), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert "# Chapter 1: Introduction" in out.read_text(encoding="utf-8")


def test_annotations_command_json_output(sample_pdf: Path, tmp_path: Path):
    out = tmp_path / "annots.json"
    result = runner.invoke(app, ["annotations", str(sample_pdf), "-o", str(out)])
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["content"] == "要確認"


def test_annotations_command_table_output(sample_pdf: Path):
    result = runner.invoke(app, ["annotations", str(sample_pdf)])
    assert result.exit_code == 0, result.output
    assert "要確認" in result.output


def test_watermark_command_requires_text_or_image(sample_pdf: Path, tmp_path: Path):
    result = runner.invoke(app, ["watermark", str(sample_pdf), "-o", str(tmp_path / "out.pdf")])
    assert result.exit_code == 1


def test_watermark_command_text(sample_pdf: Path, tmp_path: Path):
    out = tmp_path / "wm.pdf"
    result = runner.invoke(app, ["watermark", str(sample_pdf), "-o", str(out), "--text", "DRAFT"])
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_page_numbers_command(sample_pdf: Path, tmp_path: Path):
    out = tmp_path / "numbered.pdf"
    result = runner.invoke(app, ["page-numbers", str(sample_pdf), "-o", str(out)])
    assert result.exit_code == 0, result.output
    with fitz.open(out) as d:
        assert "1/6" in d[0].get_text()


def test_sanitize_command(sample_pdf: Path, tmp_path: Path):
    with fitz.open(sample_pdf) as d:
        d.set_metadata({"author": "Alex"})
        withmeta = tmp_path / "withmeta.pdf"
        d.save(withmeta)

    out = tmp_path / "sanitized.pdf"
    result = runner.invoke(app, ["sanitize", str(withmeta), "-o", str(out)])
    assert result.exit_code == 0, result.output
    with fitz.open(out) as d:
        assert d.metadata["author"] == ""


def test_rotate_command(sample_pdf: Path, tmp_path: Path):
    out = tmp_path / "rotated.pdf"
    result = runner.invoke(app, ["rotate", str(sample_pdf), "--degrees", "90", "-o", str(out)])
    assert result.exit_code == 0, result.output
    with fitz.open(out) as d:
        assert d[0].rotation == 90


def test_nup_command(sample_pdf: Path, tmp_path: Path):
    out = tmp_path / "nup.pdf"
    result = runner.invoke(app, ["nup", str(sample_pdf), "--n", "2", "-o", str(out)])
    assert result.exit_code == 0, result.output
    with fitz.open(out) as d:
        assert d.page_count == 3


def test_remove_blank_command(sample_pdf: Path, tmp_path: Path):
    out = tmp_path / "noblank.pdf"
    result = runner.invoke(app, ["remove-blank", str(sample_pdf), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert "1ページ" in result.output
