from __future__ import annotations

from diskcheck.fsutils import human_size
from diskcheck.scan import interactive_browse, scan_tree


def test_human_size_formats_units():
    assert human_size(0) == "0 B"
    assert human_size(512) == "512 B"
    assert human_size(1024) == "1.00 KB"
    assert human_size(1024 * 1024 * 3) == "3.00 MB"


def test_scan_tree_aggregates_sizes_bottom_up(sample_tree):
    root = scan_tree(sample_tree)

    assert root.is_dir
    assert root.size == 360

    sub = next(c for c in root.children if c.path.name == "sub")
    assert sub.size == 60

    nested = next(c for c in sub.children if c.path.name == "nested")
    assert nested.size == 10


def test_scan_tree_single_file():
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"x" * 42)
        path = Path(f.name)

    try:
        node = scan_tree(path)
        assert not node.is_dir
        assert node.size == 42
    finally:
        path.unlink()


def test_top_children_ranks_by_size_descending(sample_tree):
    root = scan_tree(sample_tree)
    ranked = root.top_children()

    assert [c.size for c in ranked] == sorted((c.size for c in ranked), reverse=True)
    assert ranked[0].path.name == "big.bin"


def test_top_children_respects_limit(sample_tree):
    root = scan_tree(sample_tree)
    assert len(root.top_children(top=1)) == 1


def test_to_dict_is_json_serializable(sample_tree):
    import json

    root = scan_tree(sample_tree)
    data = root.to_dict(top=10)

    serialized = json.dumps(data)
    assert json.loads(serialized)["size"] == 360
    assert data["is_dir"] is True
    names = {c["name"] for c in data["children"]}
    assert names == {"big.bin", "sub"}


def test_scan_tree_skips_unreadable_entries_gracefully(tmp_path, monkeypatch):
    import os

    (tmp_path / "ok.bin").write_bytes(b"x" * 10)

    real_scandir = os.scandir

    def broken_scandir(path):
        if str(path) == str(tmp_path):
            raise PermissionError("denied")
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", broken_scandir)

    node = scan_tree(tmp_path)
    assert node.error is not None
    assert node.size == 0


def test_interactive_browse_drills_down_and_quits(sample_tree, capsys):
    from rich.console import Console

    root = scan_tree(sample_tree)
    console = Console(force_terminal=False)

    # Ranked top-level children: big.bin (300), sub (60). Pick "2" to enter sub/, then quit.
    inputs = iter(["2", "q"])
    monkeypatched_input = lambda prompt="": next(inputs)
    console.input = monkeypatched_input

    interactive_browse(root, top=20, console=console)

    output = capsys.readouterr().out
    assert "sub" in output
    assert "nested" in output
