from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

from kanbancli.file import existing_ids, find_task, load_tasks, save_tasks
from kanbancli.recur import generate_next_occurrence
from kanbancli.task import Task, generate_id, resolve_status_token


class TaskNotFoundError(ValueError):
    pass


def add_task(
    tasks: list[Task],
    content: str,
    priority: int = 0,
    due: Optional[date] = None,
    tags: Optional[list[str]] = None,
    depends: Optional[list[str]] = None,
    parent_id: Optional[str] = None,
    today: Optional[date] = None,
) -> Task:
    """Appends (or, with `parent_id`, inserts as a subtask right after
    its parent and any of the parent's existing deeper-level
    descendants) a new TODO task and returns it. Mutates `tasks`
    in-place."""
    today = today or date.today()
    level = 0
    insert_index = len(tasks)

    if parent_id is not None:
        parent = find_task(tasks, parent_id)
        if parent is None:
            raise TaskNotFoundError(f"parent task '{parent_id}' not found")
        level = parent.level + 1
        parent_idx = tasks.index(parent)
        insert_index = parent_idx + 1
        while insert_index < len(tasks) and tasks[insert_index].level > parent.level:
            insert_index += 1

    new_task = Task(
        id=generate_id(existing_ids(tasks)),
        content=content,
        status_token=" ",
        priority=priority,
        add_date=today,
        due_date=due,
        tags=list(tags or []),
        depends=list(depends or []),
        level=level,
    )
    tasks.insert(insert_index, new_task)
    return new_task


def update_status(
    tasks: list[Task], task_id: str, status_value: str, today: Optional[date] = None
) -> tuple[Task, Optional[Task]]:
    """Updates a task's status (raw token or friendly alias -- see
    task.STATUS_ALIASES). If this transitions the task into "done" and
    it has an `@recur`, a fresh next-occurrence task is appended and
    returned as the second element (None otherwise)."""
    task = find_task(tasks, task_id)
    if task is None:
        raise TaskNotFoundError(f"task '{task_id}' not found")

    was_done = task.is_done
    task.status_token = resolve_status_token(status_value)

    generated = None
    if task.is_done and not was_done and task.recur:
        generated = generate_next_occurrence(task, tasks, today)
        tasks.append(generated)

    return task, generated


def is_blocked(task: Task, tasks: list[Task]) -> bool:
    """A task is blocked while any of its @depends ids points at a task
    that still exists and isn't done. A @depends id that no longer
    resolves to anything (e.g. the blocker was archived) does NOT
    count as blocking -- otherwise archiving a dependency would leave
    its dependents permanently stuck."""
    for dep_id in task.depends:
        dep = find_task(tasks, dep_id)
        if dep is not None and not dep.is_done:
            return True
    return False


def list_tasks(
    tasks: list[Task],
    sort_by: Optional[str] = None,
    available_only: bool = False,
    tag: Optional[str] = None,
    status: Optional[str] = None,
) -> list[Task]:
    result = list(tasks)

    if tag:
        result = [t for t in result if tag in t.tags]
    if status:
        result = [t for t in result if t.category == status]
    if available_only:
        result = [t for t in result if t.category not in ("done", "cancelled") and not is_blocked(t, tasks)]

    if sort_by == "priority":
        result.sort(key=lambda t: -t.priority)
    elif sort_by == "due":
        result.sort(key=lambda t: (t.due_date is None, t.due_date or date.max))

    return result


def filter_tasks(
    tasks: list[Task],
    tags: Optional[list[str]] = None,
    statuses: Optional[list[str]] = None,
    due_before: Optional[date] = None,
) -> list[Task]:
    result = list(tasks)
    if tags:
        result = [t for t in result if any(tag in t.tags for tag in tags)]
    if statuses:
        result = [t for t in result if t.category in statuses]
    if due_before:
        result = [t for t in result if t.due_date is not None and t.due_date < due_before]
    return result


def export_tasks(tasks: list[Task], output_path: Path) -> int:
    save_tasks(output_path, tasks)
    return len(tasks)


def archive_tasks(tasks: list[Task], archive_path: Path) -> tuple[list[Task], list[Task]]:
    """Splits `tasks` into (remaining, archived) by each task's own
    done/cancelled status (independent of parent/child relation -- a
    completed parent does not force its still-open subtasks to archive
    too) and appends `archived` onto whatever's already in
    `archive_path`. Returns both lists; saving `remaining` back to the
    main file is the caller's responsibility."""
    remaining = [t for t in tasks if not t.is_terminal]
    archived = [t for t in tasks if t.is_terminal]

    existing_archive = load_tasks(archive_path)
    save_tasks(archive_path, existing_archive + archived)

    return remaining, archived
