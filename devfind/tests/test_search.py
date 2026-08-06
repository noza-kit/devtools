from __future__ import annotations

from pathlib import Path

from devfind.search import (
    CONTENT,
    NAME,
    Match,
    build_fd_command,
    build_rg_command,
    merge_results,
    run_fd,
    run_rg,
)


def test_build_fd_command_includes_excludes_and_targets():
    cmd = build_fd_command("keyword", [Path("/a"), Path("/b")], ["venv", ".git"])

    assert cmd[0] == "fd"
    assert "--exclude" in cmd
    assert cmd.count("--exclude") == 2
    assert "venv" in cmd
    assert ".git" in cmd
    assert "keyword" in cmd
    assert str(Path("/a")) in cmd
    assert str(Path("/b")) in cmd


def test_build_rg_command_uses_files_with_matches_and_negated_globs():
    cmd = build_rg_command("keyword", [Path("/a")], ["node_modules"])

    assert cmd[0] == "rg"
    assert "--files-with-matches" in cmd
    assert "--glob" in cmd
    assert "!node_modules" in cmd
    assert "keyword" in cmd


def test_run_fd_parses_stdout_into_lines(fake_subprocess_run):
    fake_subprocess_run({"fd": "a/one.txt\na/two.txt\n"})

    result = run_fd("kw", [Path("/a")], [])

    assert result == ["a/one.txt", "a/two.txt"]


def test_run_fd_ignores_blank_lines(fake_subprocess_run):
    fake_subprocess_run({"fd": "a/one.txt\n\n\na/two.txt\n"})

    result = run_fd("kw", [Path("/a")], [])

    assert result == ["a/one.txt", "a/two.txt"]


def test_run_rg_returns_empty_list_when_no_matches(fake_subprocess_run):
    # rg exits 1 with empty stdout when nothing matches; that must not be
    # treated as an error, just an empty result.
    fake_subprocess_run({"rg": ""}, {"rg": 1})

    result = run_rg("kw", [Path("/a")], [])

    assert result == []


def test_merge_results_name_matches_come_first():
    matches = merge_results(["a/one.txt", "a/two.txt"], ["a/three.txt"])

    assert matches == [
        Match(NAME, "a/one.txt"),
        Match(NAME, "a/two.txt"),
        Match(CONTENT, "a/three.txt"),
    ]


def test_merge_results_dedupes_content_matches_already_found_by_name():
    matches = merge_results(["a/one.txt", "a/two.txt"], ["a/two.txt", "a/three.txt"])

    assert matches == [
        Match(NAME, "a/one.txt"),
        Match(NAME, "a/two.txt"),
        Match(CONTENT, "a/three.txt"),
    ]
    # a/two.txt only appears once, under NAME.
    assert sum(1 for m in matches if m.path == "a/two.txt") == 1


def test_merge_results_dedupes_equivalent_paths_with_different_spelling():
    matches = merge_results(["a/one.txt"], ["./a/one.txt"])

    assert matches == [Match(NAME, "a/one.txt")]


def test_merge_results_dedupes_within_fd_results_itself():
    matches = merge_results(["a/one.txt", "a/one.txt"], [])

    assert matches == [Match(NAME, "a/one.txt")]


def test_merge_results_empty_inputs_returns_empty_list():
    assert merge_results([], []) == []


def test_merge_results_only_content_matches():
    matches = merge_results([], ["a/one.txt"])

    assert matches == [Match(CONTENT, "a/one.txt")]
