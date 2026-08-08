from __future__ import annotations

from projarchive import scan


def test_scan_large_files_finds_files_at_or_above_threshold(tmp_path):
    (tmp_path / "small.txt").write_bytes(b"x" * 10)
    (tmp_path / "big.bin").write_bytes(b"x" * 100)

    found = scan.scan_large_files(tmp_path, threshold_bytes=100)

    assert [lf.path.name for lf in found] == ["big.bin"]
    assert found[0].size_bytes == 100


def test_scan_large_files_searches_recursively(tmp_path):
    nested = tmp_path / "data" / "models"
    nested.mkdir(parents=True)
    (nested / "checkpoint.pt").write_bytes(b"x" * 200)

    found = scan.scan_large_files(tmp_path, threshold_bytes=100)

    assert len(found) == 1
    assert found[0].path == nested / "checkpoint.pt"


def test_scan_large_files_returns_largest_first(tmp_path):
    (tmp_path / "a.bin").write_bytes(b"x" * 150)
    (tmp_path / "b.bin").write_bytes(b"x" * 300)

    found = scan.scan_large_files(tmp_path, threshold_bytes=100)

    assert [lf.path.name for lf in found] == ["b.bin", "a.bin"]


def test_scan_large_files_returns_empty_when_nothing_qualifies(tmp_path):
    (tmp_path / "small.txt").write_bytes(b"x" * 10)

    assert scan.scan_large_files(tmp_path, threshold_bytes=100) == []
