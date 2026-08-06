from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

import kanbancli.cli as cli_module
from kanbancli.cli import app
from kanbancli.file import load_tasks

runner = CliRunner()


@pytest.fixture(autouse=True)
def fake_notify(monkeypatch):
    calls = []

    def fake(message, channels=None, *, config=None):
        calls.append((message, channels, config))
        return {}

    monkeypatch.setattr("kanbancli.remind.notify", fake)
    return calls


def test_add_with_all_options(tmp_path: Path):
    file_path = tmp_path / "tasks.md"
    result = runner.invoke(
        app,
        ["add", "Write report", "--due", "2026-08-10", "--priority", "!!", "--tags", "work,urgent", "-f", str(file_path)],
    )
    assert result.exit_code == 0, result.output
    tasks = load_tasks(file_path)
    assert len(tasks) == 1
    assert tasks[0].content == "Write report"
    assert tasks[0].priority == 2
    assert tasks[0].tags == ["work", "urgent"]


def test_add_interactive_prompts(tmp_path: Path):
    file_path = tmp_path / "tasks.md"
    result = runner.invoke(app, ["add", "-f", str(file_path)], input="Buy milk\n\n\n\n")
    assert result.exit_code == 0, result.output
    tasks = load_tasks(file_path)
    assert tasks[0].content == "Buy milk"


def test_add_invalid_priority_fails(tmp_path: Path):
    file_path = tmp_path / "tasks.md"
    result = runner.invoke(app, ["add", "Task", "--priority", "high", "-f", str(file_path)])
    assert result.exit_code == 1


def test_add_invalid_recur_fails_fast(tmp_path: Path):
    file_path = tmp_path / "tasks.md"
    result = runner.invoke(app, ["add", "Task", "--recur", "weekly", "-f", str(file_path)])
    assert result.exit_code == 1
    assert load_tasks(file_path) == []  # nothing written on failure


def test_add_subtask(tmp_path: Path):
    file_path = tmp_path / "tasks.md"
    runner.invoke(app, ["add", "Parent", "-f", str(file_path)])
    parent_id = load_tasks(file_path)[0].id
    result = runner.invoke(app, ["add", "Child", "--parent", parent_id, "-f", str(file_path)])
    assert result.exit_code == 0, result.output
    tasks = load_tasks(file_path)
    assert tasks[1].level == 1


def test_update_status(tmp_path: Path):
    file_path = tmp_path / "tasks.md"
    runner.invoke(app, ["add", "Task", "-f", str(file_path)])
    task_id = load_tasks(file_path)[0].id
    result = runner.invoke(app, ["update", task_id, "done", "-f", str(file_path)])
    assert result.exit_code == 0, result.output
    assert load_tasks(file_path)[0].status_token == "x"


def test_update_missing_task_fails(tmp_path: Path):
    file_path = tmp_path / "tasks.md"
    result = runner.invoke(app, ["update", "zzzz", "done", "-f", str(file_path)])
    assert result.exit_code == 1


def test_update_recurring_task_generates_next(tmp_path: Path):
    file_path = tmp_path / "tasks.md"
    runner.invoke(app, ["add", "Weekly", "--due", "2026-08-07", "--recur", "1w", "-f", str(file_path)])
    task_id = load_tasks(file_path)[0].id
    result = runner.invoke(app, ["update", task_id, "done", "-f", str(file_path)])
    assert result.exit_code == 0, result.output
    assert len(load_tasks(file_path)) == 2


def test_list_shows_added_task(tmp_path: Path):
    file_path = tmp_path / "tasks.md"
    runner.invoke(app, ["add", "Visible task", "-f", str(file_path)])
    result = runner.invoke(app, ["list", "-f", str(file_path)])
    assert result.exit_code == 0, result.output
    assert "Visible task" in result.output


def test_list_empty_file_message(tmp_path: Path):
    file_path = tmp_path / "tasks.md"
    result = runner.invoke(app, ["list", "-f", str(file_path)])
    assert result.exit_code == 0
    assert "ありません" in result.output


def test_list_available_filters_blocked(tmp_path: Path):
    file_path = tmp_path / "tasks.md"
    runner.invoke(app, ["add", "Dep", "-f", str(file_path)])
    dep_id = load_tasks(file_path)[0].id
    runner.invoke(app, ["add", "Blocked", "--depends", dep_id, "-f", str(file_path)])
    result = runner.invoke(app, ["list", "--available", "-f", str(file_path)])
    assert "Blocked" not in result.output
    assert "Dep" in result.output


def test_export_writes_filtered_file(tmp_path: Path):
    file_path = tmp_path / "tasks.md"
    runner.invoke(app, ["add", "Tagged", "--tags", "work", "-f", str(file_path)])
    runner.invoke(app, ["add", "Untagged", "-f", str(file_path)])
    output = tmp_path / "export.md"
    result = runner.invoke(app, ["export", str(output), "--tags", "work", "-f", str(file_path)])
    assert result.exit_code == 0, result.output
    exported = load_tasks(output)
    assert len(exported) == 1
    assert exported[0].content == "Tagged"


def test_archive_moves_done_tasks(tmp_path: Path):
    file_path = tmp_path / "tasks.md"
    runner.invoke(app, ["add", "Done task", "-f", str(file_path)])
    task_id = load_tasks(file_path)[0].id
    runner.invoke(app, ["update", task_id, "done", "-f", str(file_path)])

    result = runner.invoke(app, ["archive", "-f", str(file_path)])
    assert result.exit_code == 0, result.output
    assert load_tasks(file_path) == []
    assert len(load_tasks(file_path.parent / "archive.md")) == 1


def test_remind_no_due_tasks(tmp_path: Path, fake_notify):
    file_path = tmp_path / "tasks.md"
    runner.invoke(app, ["add", "No due date", "-f", str(file_path)])
    result = runner.invoke(app, ["remind", "-f", str(file_path)])
    assert result.exit_code == 0, result.output
    assert fake_notify == []


def test_remind_sends_notification_for_due_task(tmp_path: Path, fake_notify):
    from datetime import date, timedelta

    file_path = tmp_path / "tasks.md"
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    runner.invoke(app, ["add", "Due soon", "--due", tomorrow, "-f", str(file_path)])
    result = runner.invoke(app, ["remind", "-f", str(file_path)])
    assert result.exit_code == 0, result.output
    assert len(fake_notify) == 1


def test_setup_autostart_register(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(cli_module, "register_autostart", lambda **kwargs: None)
    result = runner.invoke(app, ["setup-autostart", "-f", str(tmp_path / "tasks.md")])
    assert result.exit_code == 0, result.output
    assert "登録しました" in result.output


def test_setup_autostart_remove(monkeypatch):
    monkeypatch.setattr(cli_module, "remove_autostart", lambda **kwargs: None)
    result = runner.invoke(app, ["setup-autostart", "--remove"])
    assert result.exit_code == 0, result.output
    assert "削除しました" in result.output


def test_setup_autostart_reports_schtasks_failure(monkeypatch):
    from kanbancli.autostart import AutostartError

    def raise_error(**kwargs):
        raise AutostartError("schtasks failed")

    monkeypatch.setattr(cli_module, "register_autostart", raise_error)
    result = runner.invoke(app, ["setup-autostart"])
    assert result.exit_code == 1
