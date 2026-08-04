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
