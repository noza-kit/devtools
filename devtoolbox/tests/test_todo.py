from typer.testing import CliRunner

from devtoolbox.todo.cli import app

runner = CliRunner()


def test_add_and_list(devtoolbox_home):
    result = runner.invoke(app, ["add", "buy milk", "--tags", "errand"])
    assert result.exit_code == 0, result.output
    assert "#1" in result.output

    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0, result.output
    assert "#1 buy milk [errand]" in result.output


def test_done_hides_from_default_list_but_shows_with_all(devtoolbox_home):
    runner.invoke(app, ["add", "task one"])

    result = runner.invoke(app, ["done", "1"])
    assert result.exit_code == 0, result.output

    result = runner.invoke(app, ["list"])
    assert "task one" not in result.output

    result = runner.invoke(app, ["list", "--all"])
    assert "[x] #1 task one" in result.output


def test_undone_reverts_done(devtoolbox_home):
    runner.invoke(app, ["add", "task one"])
    runner.invoke(app, ["done", "1"])

    result = runner.invoke(app, ["undone", "1"])
    assert result.exit_code == 0, result.output

    result = runner.invoke(app, ["list"])
    assert "task one" in result.output


def test_done_nonexistent_fails(devtoolbox_home):
    result = runner.invoke(app, ["done", "999"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_rm_deletes_task(devtoolbox_home):
    runner.invoke(app, ["add", "task one"])
    result = runner.invoke(app, ["rm", "1"])
    assert result.exit_code == 0, result.output

    result = runner.invoke(app, ["list", "--all"])
    assert "task one" not in result.output


def test_rm_nonexistent_fails(devtoolbox_home):
    result = runner.invoke(app, ["rm", "999"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_list_multi_tag_filter_requires_all_tags(devtoolbox_home):
    runner.invoke(app, ["add", "task a", "--tags", "work,urgent"])
    runner.invoke(app, ["add", "task b", "--tags", "work"])

    result = runner.invoke(app, ["list", "--tag", "work", "--tag", "urgent"])
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert any(line.startswith("[ ] #1") for line in lines)
    assert not any(line.startswith("[ ] #2") for line in lines)


def test_export_writes_markdown_checklist_including_done_by_default(devtoolbox_home, tmp_path):
    runner.invoke(app, ["add", "buy milk", "--tags", "errand"])
    runner.invoke(app, ["add", "write report"])
    runner.invoke(app, ["done", "2"])

    output_file = tmp_path / "TODO.md"
    result = runner.invoke(app, ["export", "--output", str(output_file)])
    assert result.exit_code == 0, result.output
    assert "Exported 2 task(s)" in result.output

    text = output_file.read_text(encoding="utf-8")
    assert text.startswith("# TODO")
    assert "- [ ] buy milk `errand`" in text
    assert "- [x] write report" in text


def test_export_pending_only_excludes_done_tasks(devtoolbox_home, tmp_path):
    runner.invoke(app, ["add", "buy milk"])
    runner.invoke(app, ["add", "write report"])
    runner.invoke(app, ["done", "2"])

    output_file = tmp_path / "TODO.md"
    result = runner.invoke(
        app, ["export", "--output", str(output_file), "--pending-only"]
    )
    assert result.exit_code == 0, result.output

    text = output_file.read_text(encoding="utf-8")
    assert "buy milk" in text
    assert "write report" not in text


def test_export_defaults_to_todo_md_in_cwd(devtoolbox_home, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["add", "buy milk"])

    result = runner.invoke(app, ["export"])
    assert result.exit_code == 0, result.output

    default_file = tmp_path / "TODO.md"
    assert default_file.exists()
    assert "buy milk" in default_file.read_text(encoding="utf-8")
