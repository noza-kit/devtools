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
