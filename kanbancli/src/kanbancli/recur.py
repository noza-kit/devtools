from __future__ import annotations

import calendar
import re
from datetime import date, timedelta
from typing import Optional

from kanbancli.file import existing_ids
from kanbancli.task import Task, generate_id

_RECUR_RE = re.compile(r"^(\d+)([dwmy])$")


class RecurError(ValueError):
    pass


def parse_recur_spec(spec: str) -> tuple[int, str]:
    m = _RECUR_RE.match(spec)
    if not m:
        raise RecurError(f"invalid @recur value '{spec}' (expected e.g. '1d', '2w', '1m', '1y')")
    return int(m.group(1)), m.group(2)


def add_interval(base: date, spec: str) -> date:
    n, unit = parse_recur_spec(spec)
    if unit == "d":
        return base + timedelta(days=n)
    if unit == "w":
        return base + timedelta(weeks=n)
    if unit == "m":
        return _add_months(base, n)
    if unit == "y":
        return _add_months(base, n * 12)
    raise RecurError(f"unhandled recur unit '{unit}'")  # unreachable given the regex, kept for safety


def _add_months(base: date, months: int) -> date:
    total_month_index = base.month - 1 + months
    year = base.year + total_month_index // 12
    month = total_month_index % 12 + 1
    day = min(base.day, calendar.monthrange(year, month)[1])  # clamp e.g. Jan 31 + 1mo -> Feb 28/29
    return date(year, month, day)


def generate_next_occurrence(task: Task, tasks: list[Task], today: Optional[date] = None) -> Task:
    """A completed recurring task (non-empty `task.recur`) produces a
    fresh TODO task with the same content/priority/tags/recur, and a
    due date advanced by the recur interval **from the original due
    date** (not from today/completion date) -- so a "every Friday"
    weekly report task stays anchored to Fridays even if it's actually
    completed on a Thursday or a following Monday."""
    if not task.recur:
        raise RecurError(f"task {task.id} has no @recur value")

    today = today or date.today()
    next_due = add_interval(task.due_date, task.recur) if task.due_date else None

    return Task(
        id=generate_id(existing_ids(tasks)),
        content=task.content,
        status_token=" ",
        priority=task.priority,
        add_date=today,
        due_date=next_due,
        recur=task.recur,
        depends=[],
        tags=list(task.tags),
        level=task.level,
    )
