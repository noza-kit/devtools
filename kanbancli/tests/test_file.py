from pathlib import Path

import pytest

from kanbancli.file import find_task, load_tasks, resolve_task_file, save_tasks
from kanbancli.task import Task, TaskParseError


def test_load_missing_file_returns_empty_list(tmp_path: Path):
    assert load_tasks(tmp_path / "does-not-exist.md") == []


def test_save_then_load_round_trip(tmp_path: Path):
    path = tmp_path / "tasks.md"
    tasks = [
        Task(id="aaaa", content="Task A", status_token=" ", priority=2),
        Task(id="bbbb", content="Task B", status_token="x", level=1),
    ]
    save_tasks(path, tasks)
    reloaded = load_tasks(path)
    assert [t.id for t in reloaded] == ["aaaa", "bbbb"]
    assert reloaded[0].priority == 2
    assert reloaded[1].level == 1


def test_load_skips_blank_lines(tmp_path: Path):
    path = tmp_path / "tasks.md"
    path.write_text("- [ ] a id:aaaa\n\n\n- [ ] b id:bbbb\n", encoding="utf-8")
    tasks = load_tasks(path)
    assert len(tasks) == 2


def test_load_bad_line_raises_with_file_and_line_number(tmp_path: Path):
    path = tmp_path / "tasks.md"
    path.write_text("- [ ] a id:aaaa\n- [ ] missing id field\n", encoding="utf-8")
    with pytest.raises(TaskParseError, match=r"tasks\.md:2"):
        load_tasks(path)


def test_find_task_by_id():
    tasks = [Task(id="aaaa", content="a"), Task(id="bbbb", content="b")]
    assert find_task(tasks, "bbbb").content == "b"
    assert find_task(tasks, "zzzz") is None


def test_resolve_explicit_path_wins(tmp_path: Path):
    explicit = tmp_path / "explicit.md"
    assert resolve_task_file(explicit=explicit) == explicit


def test_resolve_finds_local_kanban_md_in_cwd(tmp_path: Path):
    local = tmp_path / ".kanban.md"
    local.write_text("", encoding="utf-8")
    assert resolve_task_file(start_dir=tmp_path) == local


def test_resolve_finds_local_kanban_md_in_parent_dir(tmp_path: Path):
    local = tmp_path / ".kanban.md"
    local.write_text("", encoding="utf-8")
    subdir = tmp_path / "sub" / "deeper"
    subdir.mkdir(parents=True)
    assert resolve_task_file(start_dir=subdir) == local


def test_resolve_falls_back_to_global_when_no_local_file(tmp_path: Path):
    subdir = tmp_path / "sub"
    subdir.mkdir()
    result = resolve_task_file(start_dir=subdir)
    assert result.name == "tasks.md"
    assert ".kanban.md" not in str(result)
