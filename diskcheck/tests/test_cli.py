from __future__ import annotations

import json

from typer.testing import CliRunner

from diskcheck.cli import app

runner = CliRunner()


def test_scan_missing_path_fails(tmp_path):
    result = runner.invoke(app, ["scan", str(tmp_path / "missing")])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_scan_prints_tree_by_default(sample_tree):
    result = runner.invoke(app, ["scan", str(sample_tree)])
    assert result.exit_code == 0, result.output
    assert "big.bin" in result.output
    assert "sub" in result.output


def test_scan_json_output_is_valid(sample_tree):
    result = runner.invoke(app, ["scan", str(sample_tree), "--json"])
    assert result.exit_code == 0, result.output

    data = json.loads(result.output)
    assert data["size"] == 360
    assert data["is_dir"] is True


def test_scan_top_limits_children_shown(sample_tree):
    result = runner.invoke(app, ["scan", str(sample_tree), "--json", "--top", "1"])
    assert result.exit_code == 0, result.output

    data = json.loads(result.output)
    assert len(data["children"]) == 1
    assert data["children"][0]["name"] == "big.bin"


def test_scan_depth_limits_recursion(sample_tree):
    result = runner.invoke(app, ["scan", str(sample_tree), "--json", "--depth", "1"])
    assert result.exit_code == 0, result.output

    data = json.loads(result.output)
    sub = next(c for c in data["children"] if c["name"] == "sub")
    assert sub["children"] == []


def test_dupes_missing_path_fails(tmp_path):
    result = runner.invoke(app, ["dupes", str(tmp_path / "missing")])
    assert result.exit_code == 1
    assert "not a directory" in result.output.lower()


def test_dupes_no_duplicates_reports_cleanly(tmp_path, make_file):
    make_file(tmp_path / "a.bin", 20)

    result = runner.invoke(app, ["dupes", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "No duplicate files found" in result.output


def test_dupes_default_is_dry_run(tmp_path, make_file):
    a = make_file(tmp_path / "a.bin", 20)
    b = make_file(tmp_path / "b.bin", 20)

    result = runner.invoke(app, ["dupes", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "dry run" in result.output.lower()
    assert a.exists() and b.exists()


def test_dupes_json_output_is_valid(tmp_path, make_file):
    make_file(tmp_path / "a.bin", 20)
    make_file(tmp_path / "b.bin", 20)

    result = runner.invoke(app, ["dupes", str(tmp_path), "--json"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert len(data) == 1
    assert len(data[0]["files"]) == 2


def test_dupes_interactive_deletes_selected_files(tmp_path, make_file):
    a = make_file(tmp_path / "a.bin", 20)
    b = make_file(tmp_path / "b.bin", 20)

    result = runner.invoke(app, ["dupes", str(tmp_path), "--interactive", "--yes"], input="1\n")

    assert result.exit_code == 0, result.output
    remaining = [p for p in (a, b) if p.exists()]
    assert len(remaining) == 1
    assert "Deleted 1 file" in result.output


def test_stale_missing_path_fails(tmp_path):
    result = runner.invoke(app, ["stale", str(tmp_path / "missing")])
    assert result.exit_code == 1
    assert "not a directory" in result.output.lower()


def test_stale_finds_old_files_by_extension(tmp_path):
    import os
    import time

    old_exe = tmp_path / "old.exe"
    old_exe.write_bytes(b"x" * 50)
    target = time.time() - 200 * 86400
    os.utime(old_exe, (target, target))

    result = runner.invoke(app, ["stale", str(tmp_path), "--older-than", "180"])

    assert result.exit_code == 0, result.output
    assert "old.exe" in result.output


def test_stale_json_output_is_valid(tmp_path):
    import json
    import os
    import time

    old_exe = tmp_path / "old.exe"
    old_exe.write_bytes(b"x" * 50)
    target = time.time() - 200 * 86400
    os.utime(old_exe, (target, target))

    result = runner.invoke(app, ["stale", str(tmp_path), "--older-than", "180", "--json"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["path"].endswith("old.exe")


def test_stale_no_matches_reports_cleanly(tmp_path):
    result = runner.invoke(app, ["stale", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "No stale files found" in result.output


def test_stale_custom_extensions_flag_overrides_defaults(tmp_path):
    import os
    import time

    old_iso = tmp_path / "old.iso"
    old_iso.write_bytes(b"x" * 50)
    target = time.time() - 200 * 86400
    os.utime(old_iso, (target, target))

    result = runner.invoke(app, ["stale", str(tmp_path), "--extensions", ".iso", "--older-than", "180"])

    assert result.exit_code == 0, result.output
    assert "old.iso" in result.output


def test_stale_never_deletes_files(tmp_path):
    import os
    import time

    old_exe = tmp_path / "old.exe"
    old_exe.write_bytes(b"x" * 50)
    target = time.time() - 200 * 86400
    os.utime(old_exe, (target, target))

    runner.invoke(app, ["stale", str(tmp_path), "--older-than", "180"])

    assert old_exe.exists()
