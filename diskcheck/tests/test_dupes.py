from __future__ import annotations

import json

from diskcheck.dupes import find_duplicate_groups, hash_file, interactive_resolve


def test_hash_file_is_deterministic_and_content_sensitive(tmp_path, make_file):
    a = make_file(tmp_path / "a.bin", 100)
    b = make_file(tmp_path / "b.bin", 100)
    assert hash_file(a) == hash_file(b)

    c = tmp_path / "c.bin"
    c.write_bytes(b"y" * 100)
    assert hash_file(a) != hash_file(c)


def test_find_duplicate_groups_detects_identical_content(tmp_path, make_file):
    make_file(tmp_path / "a.bin", 50)
    make_file(tmp_path / "sub" / "b.bin", 50)
    make_file(tmp_path / "unique.bin", 999)  # different size, different content

    groups = find_duplicate_groups(tmp_path)

    assert len(groups) == 1
    group = groups[0]
    assert group.size == 50
    assert len(group.files) == 2
    paths = {f.path.name for f in group.files}
    assert paths == {"a.bin", "b.bin"}


def test_same_size_different_content_is_not_a_duplicate(tmp_path):
    (tmp_path / "a.bin").write_bytes(b"x" * 50)
    (tmp_path / "b.bin").write_bytes(b"y" * 50)

    groups = find_duplicate_groups(tmp_path)

    assert groups == []


def test_min_size_filters_small_files(tmp_path, make_file):
    make_file(tmp_path / "a.bin", 10)
    make_file(tmp_path / "b.bin", 10)

    groups = find_duplicate_groups(tmp_path, min_size=50)

    assert groups == []


def test_wasted_bytes_accounts_for_extra_copies(tmp_path, make_file):
    make_file(tmp_path / "a.bin", 100)
    make_file(tmp_path / "b.bin", 100)
    make_file(tmp_path / "c.bin", 100)

    groups = find_duplicate_groups(tmp_path)

    assert len(groups) == 1
    assert groups[0].wasted_bytes == 200  # 3 copies, 2 reclaimable


def test_groups_sorted_by_wasted_bytes_descending(tmp_path, make_file):
    # Small group with many copies wastes more than a large group with 2 copies, if sizes are close.
    make_file(tmp_path / "big1.bin", 1000)
    make_file(tmp_path / "big2.bin", 1000)
    make_file(tmp_path / "small1.bin", 10)
    make_file(tmp_path / "small2.bin", 10)
    make_file(tmp_path / "small3.bin", 10)
    make_file(tmp_path / "small4.bin", 10)

    groups = find_duplicate_groups(tmp_path)

    assert groups[0].size == 1000  # 1000 bytes wasted > 30 bytes wasted
    assert groups[0].wasted_bytes == 1000


def test_to_dict_is_json_serializable(tmp_path, make_file):
    make_file(tmp_path / "a.bin", 20)
    make_file(tmp_path / "b.bin", 20)

    groups = find_duplicate_groups(tmp_path)
    data = [g.to_dict() for g in groups]

    serialized = json.dumps(data)
    parsed = json.loads(serialized)
    assert parsed[0]["size"] == 20
    assert len(parsed[0]["files"]) == 2


def test_interactive_resolve_deletes_all_but_kept_file(tmp_path, make_file):
    from rich.console import Console

    a = make_file(tmp_path / "a.bin", 30)
    b = make_file(tmp_path / "b.bin", 30)
    groups = find_duplicate_groups(tmp_path)
    assert len(groups) == 1

    console = Console(force_terminal=False)
    # Keep index 1 (whichever sorts first by mtime desc), confirm deletion with "y".
    inputs = iter(["1", "y"])
    console.input = lambda prompt="": next(inputs)

    deleted, freed = interactive_resolve(groups, yes=False, console=console)

    assert deleted == 1
    assert freed == 30
    remaining = [p for p in (a, b) if p.exists()]
    assert len(remaining) == 1


def test_interactive_resolve_skip_leaves_files_untouched(tmp_path, make_file):
    from rich.console import Console

    a = make_file(tmp_path / "a.bin", 30)
    b = make_file(tmp_path / "b.bin", 30)
    groups = find_duplicate_groups(tmp_path)

    console = Console(force_terminal=False)
    inputs = iter(["s"])
    console.input = lambda prompt="": next(inputs)

    deleted, freed = interactive_resolve(groups, yes=True, console=console)

    assert deleted == 0
    assert freed == 0
    assert a.exists() and b.exists()


def test_interactive_resolve_yes_skips_confirmation_prompt(tmp_path, make_file):
    from rich.console import Console

    make_file(tmp_path / "a.bin", 30)
    make_file(tmp_path / "b.bin", 30)
    groups = find_duplicate_groups(tmp_path)

    console = Console(force_terminal=False)
    # Only one input needed (keep choice); yes=True must skip the confirm prompt.
    inputs = iter(["1"])
    console.input = lambda prompt="": next(inputs)

    deleted, freed = interactive_resolve(groups, yes=True, console=console)

    assert deleted == 1
    assert freed == 30
