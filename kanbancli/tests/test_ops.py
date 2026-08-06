from datetime import date
from pathlib import Path

import pytest

from kanbancli import ops
from kanbancli.file import load_tasks
from kanbancli.task import Task, TaskParseError


def test_add_task_appends_with_defaults():
    tasks = []
    t = ops.add_task(tasks, "Buy milk")
    assert t in tasks
    assert t.status_token == " "
    assert t.level == 0
    assert len(t.id) == 4


def test_add_task_as_subtask_gets_incremented_level():
    tasks = []
    parent = ops.add_task(tasks, "Parent task")
    child = ops.add_task(tasks, "Child task", parent_id=parent.id)
    assert child.level == 1


def test_add_subtask_inserted_right_after_parent():
    tasks = []
    parent = ops.add_task(tasks, "Parent")
    ops.add_task(tasks, "Unrelated top-level")
    child = ops.add_task(tasks, "Child", parent_id=parent.id)
    assert tasks.index(child) == 1  # right after parent, before "Unrelated top-level"


def test_add_subtask_after_existing_subtasks():
    tasks = []
    parent = ops.add_task(tasks, "Parent")
    child1 = ops.add_task(tasks, "Child 1", parent_id=parent.id)
    child2 = ops.add_task(tasks, "Child 2", parent_id=parent.id)
    assert [t.content for t in tasks] == ["Parent", "Child 1", "Child 2"]


def test_add_task_with_missing_parent_raises():
    tasks = []
    with pytest.raises(ops.TaskNotFoundError):
        ops.add_task(tasks, "orphan", parent_id="zzzz")


def test_update_status_changes_token():
    tasks = []
    t = ops.add_task(tasks, "Task")
    updated, generated = ops.update_status(tasks, t.id, "done")
    assert updated.status_token == "x"
    assert generated is None


def test_update_status_missing_task_raises():
    with pytest.raises(ops.TaskNotFoundError):
        ops.update_status([], "zzzz", "done")


def test_update_status_invalid_status_raises():
    tasks = [Task(id="aaaa", content="x")]
    with pytest.raises(TaskParseError):
        ops.update_status(tasks, "aaaa", "not-a-status")


def test_update_status_to_done_with_recur_generates_next():
    tasks = []
    t = ops.add_task(tasks, "Weekly report", due=date(2026, 8, 7))
    t.recur = "1w"
    _, generated = ops.update_status(tasks, t.id, "done", today=date(2026, 8, 7))
    assert generated is not None
    assert generated.due_date == date(2026, 8, 14)
    assert generated in tasks


def test_update_status_to_done_twice_does_not_regenerate():
    tasks = []
    t = ops.add_task(tasks, "Weekly report", due=date(2026, 8, 7))
    t.recur = "1w"
    ops.update_status(tasks, t.id, "done")
    _, generated_again = ops.update_status(tasks, t.id, "done")
    assert generated_again is None  # already done -> not a done transition


def test_is_blocked_true_when_dependency_incomplete():
    tasks = []
    dep = ops.add_task(tasks, "Dependency")
    blocked = ops.add_task(tasks, "Blocked", depends=[dep.id])
    assert ops.is_blocked(blocked, tasks) is True


def test_is_blocked_false_when_dependency_done():
    tasks = []
    dep = ops.add_task(tasks, "Dependency")
    blocked = ops.add_task(tasks, "Blocked", depends=[dep.id])
    ops.update_status(tasks, dep.id, "done")
    assert ops.is_blocked(blocked, tasks) is False


def test_is_blocked_false_when_dependency_missing_entirely():
    tasks = []
    orphaned = ops.add_task(tasks, "Depends on archived task", depends=["zzzz"])
    assert ops.is_blocked(orphaned, tasks) is False


def test_list_tasks_available_only_excludes_done_and_blocked():
    tasks = []
    dep = ops.add_task(tasks, "Dependency")
    blocked = ops.add_task(tasks, "Blocked", depends=[dep.id])
    free = ops.add_task(tasks, "Free task")
    result = ops.list_tasks(tasks, available_only=True)
    ids = {t.id for t in result}
    assert dep.id in ids  # dep itself has no blockers
    assert free.id in ids
    assert blocked.id not in ids


def test_list_tasks_sort_by_priority():
    tasks = []
    low = ops.add_task(tasks, "Low", priority=1)
    high = ops.add_task(tasks, "High", priority=3)
    result = ops.list_tasks(tasks, sort_by="priority")
    assert result[0].id == high.id
    assert result[-1].id == low.id


def test_list_tasks_sort_by_due_puts_none_last():
    tasks = []
    no_due = ops.add_task(tasks, "No due date")
    later = ops.add_task(tasks, "Later", due=date(2026, 12, 1))
    sooner = ops.add_task(tasks, "Sooner", due=date(2026, 1, 1))
    result = ops.list_tasks(tasks, sort_by="due")
    assert [t.id for t in result] == [sooner.id, later.id, no_due.id]


def test_list_tasks_filter_by_tag():
    tasks = []
    ops.add_task(tasks, "Tagged", tags=["work"])
    ops.add_task(tasks, "Untagged")
    result = ops.list_tasks(tasks, tag="work")
    assert len(result) == 1


def test_filter_tasks_by_multiple_tags_is_any_match():
    tasks = []
    ops.add_task(tasks, "A", tags=["work"])
    ops.add_task(tasks, "B", tags=["home"])
    ops.add_task(tasks, "C", tags=["other"])
    result = ops.filter_tasks(tasks, tags=["work", "home"])
    assert len(result) == 2


def test_filter_tasks_by_due_before():
    tasks = []
    ops.add_task(tasks, "Early", due=date(2026, 1, 1))
    ops.add_task(tasks, "Late", due=date(2026, 12, 1))
    result = ops.filter_tasks(tasks, due_before=date(2026, 6, 1))
    assert len(result) == 1
    assert result[0].content == "Early"


def test_export_tasks_writes_file(tmp_path: Path):
    tasks = []
    ops.add_task(tasks, "Task A")
    output = tmp_path / "export.md"
    count = ops.export_tasks(tasks, output)
    assert count == 1
    assert load_tasks(output)[0].content == "Task A"


def test_archive_moves_done_and_cancelled(tmp_path: Path):
    tasks = []
    done = ops.add_task(tasks, "Done task")
    cancelled = ops.add_task(tasks, "Cancelled task")
    active = ops.add_task(tasks, "Active task")
    ops.update_status(tasks, done.id, "done")
    ops.update_status(tasks, cancelled.id, "cancel")

    archive_path = tmp_path / "archive.md"
    remaining, archived = ops.archive_tasks(tasks, archive_path)

    assert [t.id for t in remaining] == [active.id]
    assert {t.id for t in archived} == {done.id, cancelled.id}
    assert {t.id for t in load_tasks(archive_path)} == {done.id, cancelled.id}


def test_archive_appends_to_existing_archive_file(tmp_path: Path):
    archive_path = tmp_path / "archive.md"
    tasks = []
    first_done = ops.add_task(tasks, "First done")
    ops.update_status(tasks, first_done.id, "done")
    ops.archive_tasks(tasks, archive_path)

    tasks2 = []
    second_done = ops.add_task(tasks2, "Second done")
    ops.update_status(tasks2, second_done.id, "done")
    ops.archive_tasks(tasks2, archive_path)

    archived_ids = {t.id for t in load_tasks(archive_path)}
    assert archived_ids == {first_done.id, second_done.id}


def test_archive_does_not_force_open_subtasks_of_a_done_parent(tmp_path: Path):
    tasks = []
    parent = ops.add_task(tasks, "Parent")
    child = ops.add_task(tasks, "Still open child", parent_id=parent.id)
    ops.update_status(tasks, parent.id, "done")

    remaining, archived = ops.archive_tasks(tasks, tmp_path / "archive.md")
    assert [t.id for t in remaining] == [child.id]
    assert [t.id for t in archived] == [parent.id]
