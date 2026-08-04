from pathlib import Path

from typer.testing import CliRunner

from devtoolbox.snip.cli import app

runner = CliRunner()


def _add(name, content, tags=""):
    args = ["add", name, "--stdin"]
    if tags:
        args += ["--tags", tags]
    return runner.invoke(app, args, input=content)


def test_add_and_get_roundtrip(devtoolbox_home):
    result = _add("hello", "print('hello world')", tags="python,demo")
    assert result.exit_code == 0, result.output

    result = runner.invoke(app, ["get", "hello"])
    assert result.exit_code == 0, result.output
    assert "print('hello world')" in result.output


def test_add_duplicate_without_overwrite_fails(devtoolbox_home):
    _add("dup", "content one")
    result = _add("dup", "content two")
    assert result.exit_code == 1
    assert "already exists" in result.output


def test_add_overwrite_replaces_content(devtoolbox_home):
    _add("dup", "content one")
    result = runner.invoke(
        app, ["add", "dup", "--stdin", "--overwrite"], input="content two"
    )
    assert result.exit_code == 0, result.output

    result = runner.invoke(app, ["get", "dup"])
    assert "content two" in result.output


def test_list_filters_by_tag(devtoolbox_home):
    _add("a", "content a", tags="foo")
    _add("b", "content b", tags="bar")

    result = runner.invoke(app, ["list", "--tag", "foo"])
    assert result.exit_code == 0, result.output
    assert "a" in result.output
    assert "b" not in result.output


def test_list_multi_tag_filter_requires_all_tags(devtoolbox_home):
    _add("a", "content a", tags="foo,bar")
    _add("b", "content b", tags="foo")

    result = runner.invoke(app, ["list", "--tag", "foo", "--tag", "bar"])
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert "a [foo, bar]" in lines
    assert not any(line.startswith("b ") for line in lines)


def test_tags_lists_all_tags_with_counts(devtoolbox_home):
    _add("a", "content a", tags="foo,bar")
    _add("b", "content b", tags="foo")

    result = runner.invoke(app, ["tags"])
    assert result.exit_code == 0, result.output
    assert "foo (2)" in result.output
    assert "bar (1)" in result.output


def test_search_matches_content(devtoolbox_home):
    _add("snippet1", "unique_marker_xyz")
    _add("snippet2", "something else")

    result = runner.invoke(app, ["search", "unique_marker_xyz"])
    assert result.exit_code == 0, result.output
    assert "snippet1" in result.output
    assert "snippet2" not in result.output


def test_rm_deletes_snippet(devtoolbox_home):
    _add("removable", "content")
    result = runner.invoke(app, ["rm", "removable", "--yes"])
    assert result.exit_code == 0, result.output

    result = runner.invoke(app, ["get", "removable"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_rm_nonexistent_fails(devtoolbox_home):
    result = runner.invoke(app, ["rm", "ghost", "--yes"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_get_copy_writes_to_clipboard(devtoolbox_home, monkeypatch):
    copied = {}
    monkeypatch.setattr(
        "devtoolbox.snip.clipboard.pyperclip.copy", lambda text: copied.setdefault("text", text)
    )
    _add("clip", "clipboard content")

    result = runner.invoke(app, ["get", "clip", "--copy"])
    assert result.exit_code == 0, result.output
    assert copied["text"] == "clipboard content"


def test_edit_updates_content_and_keeps_tags(devtoolbox_home, monkeypatch):
    _add("editable", "original content", tags="keep-me")

    def fake_run(cmd, check=True):
        Path(cmd[-1]).write_text("edited content", encoding="utf-8")

    monkeypatch.setattr("devtoolbox.snip.cli.subprocess.run", fake_run)

    result = runner.invoke(app, ["edit", "editable"])
    assert result.exit_code == 0, result.output

    result = runner.invoke(app, ["get", "editable"])
    assert "edited content" in result.output

    result = runner.invoke(app, ["list", "--tag", "keep-me"])
    assert "editable" in result.output


def test_edit_can_replace_tags(devtoolbox_home, monkeypatch):
    _add("editable2", "original content", tags="old-tag")

    def fake_run(cmd, check=True):
        Path(cmd[-1]).write_text("edited content", encoding="utf-8")

    monkeypatch.setattr("devtoolbox.snip.cli.subprocess.run", fake_run)

    result = runner.invoke(app, ["edit", "editable2", "--tags", "new-tag"])
    assert result.exit_code == 0, result.output

    result = runner.invoke(app, ["list", "--tag", "new-tag"])
    assert "editable2" in result.output
    result = runner.invoke(app, ["list", "--tag", "old-tag"])
    assert "editable2" not in result.output


def test_edit_nonexistent_fails(devtoolbox_home):
    result = runner.invoke(app, ["edit", "ghost"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_export_import_roundtrip(devtoolbox_home, tmp_path):
    _add("a", "content a", tags="foo")
    _add("b", "content b", tags="bar")

    export_file = tmp_path / "snippets.json"
    result = runner.invoke(app, ["export", "--output", str(export_file)])
    assert result.exit_code == 0, result.output
    assert export_file.exists()

    runner.invoke(app, ["rm", "a", "--yes"])
    runner.invoke(app, ["rm", "b", "--yes"])
    result = runner.invoke(app, ["list"])
    assert "No snippets found." in result.output

    result = runner.invoke(app, ["import", str(export_file)])
    assert result.exit_code == 0, result.output
    assert "Imported 2 snippet(s)" in result.output

    result = runner.invoke(app, ["get", "a"])
    assert "content a" in result.output


def test_import_skips_existing_without_overwrite(devtoolbox_home, tmp_path):
    _add("a", "original")
    export_file = tmp_path / "snippets.json"
    runner.invoke(app, ["export", "--output", str(export_file)])
    runner.invoke(app, ["add", "a", "--stdin", "--overwrite"], input="changed")

    result = runner.invoke(app, ["import", str(export_file)])
    assert result.exit_code == 0, result.output
    assert "skipped 1" in result.output

    result = runner.invoke(app, ["get", "a"])
    assert "changed" in result.output


def test_add_applies_default_tags_from_config(devtoolbox_home):
    devtoolbox_home.mkdir(parents=True, exist_ok=True)
    (devtoolbox_home / "config.yaml").write_text(
        "snip:\n  default_tags: [inbox]\n", encoding="utf-8"
    )

    _add("a", "content a", tags="foo")

    result = runner.invoke(app, ["list", "--tag", "inbox"])
    assert result.exit_code == 0, result.output
    assert "a" in result.output
