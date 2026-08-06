import csv
from pathlib import Path

import fitz
import pytest
import yaml

from pdfcraft import convert


def test_pdf_to_images_default_all_pages(sample_pdf: Path, tmp_path: Path):
    outputs = convert.pdf_to_images(sample_pdf, tmp_path / "imgs", dpi=72)
    assert len(outputs) == 6
    assert all(o.exists() and o.stat().st_size > 0 for o in outputs)


def test_pdf_to_images_page_spec_and_format(sample_pdf: Path, tmp_path: Path):
    outputs = convert.pdf_to_images(sample_pdf, tmp_path / "imgs", page_spec="1-2", fmt="jpeg", dpi=72)
    assert len(outputs) == 2
    assert all(o.suffix == ".jpg" for o in outputs)


def test_pdf_to_images_unsupported_format_raises(sample_pdf: Path, tmp_path: Path):
    with pytest.raises(ValueError):
        convert.pdf_to_images(sample_pdf, tmp_path / "imgs", fmt="bmp")


@pytest.fixture
def two_images(tmp_path: Path) -> list[Path]:
    from PIL import Image

    paths = []
    for i, color in enumerate([(255, 0, 0), (0, 255, 0)]):
        p = tmp_path / f"img{i}.png"
        Image.new("RGB", (200, 100), color).save(p)
        paths.append(p)
    return paths


def test_images_to_pdf_one_page_per_image(two_images: list[Path], tmp_path: Path):
    out = convert.images_to_pdf(two_images, tmp_path / "out.pdf", title="T", caption="C")
    with fitz.open(out) as d:
        assert d.page_count == 2
        assert "T" in d[0].get_text()
        assert "C" in d[0].get_text()


def test_load_batch_config_csv(two_images: list[Path], tmp_path: Path):
    cfg = tmp_path / "batch.csv"
    with open(cfg, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["image_path", "title", "caption"])
        for i, p in enumerate(two_images):
            w.writerow([str(p), f"T{i}", f"C{i}"])
    entries = convert.load_batch_config(cfg)
    assert len(entries) == 2
    assert entries[0].title == "T0"


def test_load_batch_config_yaml(two_images: list[Path], tmp_path: Path):
    cfg = tmp_path / "batch.yaml"
    data = [{"path": str(p), "title": f"T{i}", "caption": f"C{i}"} for i, p in enumerate(two_images)]
    cfg.write_text(yaml.safe_dump(data), encoding="utf-8")
    entries = convert.load_batch_config(cfg)
    assert len(entries) == 2


def test_load_batch_config_relative_paths_resolve_against_config_dir(tmp_path: Path):
    from PIL import Image

    subdir = tmp_path / "imgs"
    subdir.mkdir()
    Image.new("RGB", (50, 50), (0, 0, 0)).save(subdir / "a.png")
    cfg = tmp_path / "batch.yaml"
    cfg.write_text(yaml.safe_dump([{"path": "imgs/a.png", "title": "A"}]), encoding="utf-8")
    entries = convert.load_batch_config(cfg)
    assert entries[0].path == subdir / "a.png"


def test_load_batch_config_missing_path_key_raises(tmp_path: Path):
    cfg = tmp_path / "batch.yaml"
    cfg.write_text(yaml.safe_dump([{"title": "no path"}]), encoding="utf-8")
    with pytest.raises(ValueError):
        convert.load_batch_config(cfg)


def test_load_batch_config_empty_raises(tmp_path: Path):
    cfg = tmp_path / "batch.yaml"
    cfg.write_text(yaml.safe_dump([]), encoding="utf-8")
    with pytest.raises(ValueError):
        convert.load_batch_config(cfg)


def test_load_batch_config_unsupported_extension_raises(tmp_path: Path):
    cfg = tmp_path / "batch.txt"
    cfg.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        convert.load_batch_config(cfg)


def test_build_report_grid_1_one_image_per_page(two_images: list[Path], tmp_path: Path):
    entries = [convert.ReportEntry(path=p, title=f"T{i}") for i, p in enumerate(two_images)]
    out = convert.build_report(entries, tmp_path / "report.pdf", grid=1)
    with fitz.open(out) as d:
        assert d.page_count == 2


def test_build_report_grid_2_packs_two_per_page(two_images: list[Path], tmp_path: Path):
    entries = [convert.ReportEntry(path=p, caption=f"C{i}") for i, p in enumerate(two_images)]
    out = convert.build_report(entries, tmp_path / "report.pdf", grid=2)
    with fitz.open(out) as d:
        assert d.page_count == 1
        text = d[0].get_text()
        assert "C0" in text and "C1" in text


def test_build_report_invalid_grid_raises(two_images: list[Path], tmp_path: Path):
    entries = [convert.ReportEntry(path=p) for p in two_images]
    with pytest.raises(ValueError):
        convert.build_report(entries, tmp_path / "report.pdf", grid=3)
