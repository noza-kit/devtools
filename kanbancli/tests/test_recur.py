from datetime import date

import pytest

from kanbancli.recur import RecurError, add_interval, generate_next_occurrence, parse_recur_spec
from kanbancli.task import Task


def test_parse_recur_spec():
    assert parse_recur_spec("2w") == (2, "w")
    assert parse_recur_spec("1m") == (1, "m")


def test_parse_recur_spec_invalid_raises():
    with pytest.raises(RecurError):
        parse_recur_spec("weekly")


@pytest.mark.parametrize(
    "base,spec,expected",
    [
        (date(2026, 8, 7), "1d", date(2026, 8, 8)),
        (date(2026, 8, 7), "1w", date(2026, 8, 14)),
        (date(2026, 1, 15), "1m", date(2026, 2, 15)),
        (date(2026, 1, 31), "1m", date(2026, 2, 28)),  # clamped: Feb has no 31st
        (date(2024, 1, 31), "1m", date(2024, 2, 29)),  # 2024 is a leap year
        (date(2026, 1, 31), "1y", date(2027, 1, 31)),
        (date(2026, 11, 30), "3m", date(2027, 2, 28)),
    ],
)
def test_add_interval(base, spec, expected):
    assert add_interval(base, spec) == expected


def test_generate_next_occurrence_uses_original_due_not_completion_date():
    """Per project decision: a recurring task's next due date is
    computed from its own @due (not from today's completion date), so
    a weekly Friday task stays anchored to Fridays even if actually
    completed late or early."""
    task = Task(id="aaaa", content="Weekly report", status_token="x", due_date=date(2026, 8, 7), recur="1w")
    next_task = generate_next_occurrence(task, [task], today=date(2026, 8, 10))  # completed 3 days late
    assert next_task.due_date == date(2026, 8, 14)
    assert next_task.status_token == " "
    assert next_task.add_date == date(2026, 8, 10)


def test_generate_next_occurrence_preserves_content_priority_tags():
    task = Task(id="aaaa", content="Report", status_token="x", priority=2, tags=["work"], due_date=date(2026, 1, 1), recur="1w")
    next_task = generate_next_occurrence(task, [task])
    assert next_task.content == "Report"
    assert next_task.priority == 2
    assert next_task.tags == ["work"]


def test_generate_next_occurrence_without_due_date_has_no_due_date():
    task = Task(id="aaaa", content="Recurring, no due date", status_token="x", recur="1w")
    next_task = generate_next_occurrence(task, [task])
    assert next_task.due_date is None


def test_generate_next_occurrence_gets_a_fresh_id():
    task = Task(id="aaaa", content="Report", status_token="x", due_date=date(2026, 1, 1), recur="1w")
    next_task = generate_next_occurrence(task, [task])
    assert next_task.id != task.id


def test_generate_next_occurrence_without_recur_raises():
    task = Task(id="aaaa", content="Not recurring", status_token="x")
    with pytest.raises(RecurError):
        generate_next_occurrence(task, [task])


def test_generate_next_occurrence_does_not_inherit_depends():
    task = Task(id="aaaa", content="Report", status_token="x", due_date=date(2026, 1, 1), recur="1w", depends=["bbbb"])
    next_task = generate_next_occurrence(task, [task])
    assert next_task.depends == []
