from __future__ import annotations

from datetime import date

import pytest

from kanbancli import remind
from kanbancli.task import Task


class FakeNotify:
    def __init__(self):
        self.calls = []

    def __call__(self, message, channels=None, *, config=None):
        self.calls.append((message, channels, config))
        return {}


@pytest.fixture
def fake_notify(monkeypatch):
    fake = FakeNotify()
    monkeypatch.setattr(remind, "notify", fake)
    return fake


def _task(due, status_token=" ", **kwargs):
    return Task(id="aaaa", content="Task", status_token=status_token, due_date=due, **kwargs)


def test_due_soon_includes_overdue():
    tasks = [_task(date(2026, 1, 1))]
    result = remind.due_soon_tasks(tasks, within_days=3, today=date(2026, 1, 5))
    assert result == tasks


def test_due_soon_includes_within_window():
    tasks = [_task(date(2026, 1, 8))]
    result = remind.due_soon_tasks(tasks, within_days=3, today=date(2026, 1, 5))
    assert result == tasks


def test_due_soon_excludes_outside_window():
    tasks = [_task(date(2026, 2, 1))]
    result = remind.due_soon_tasks(tasks, within_days=3, today=date(2026, 1, 5))
    assert result == []


def test_due_soon_excludes_tasks_without_due_date():
    tasks = [_task(None)]
    assert remind.due_soon_tasks(tasks, today=date(2026, 1, 5)) == []


def test_due_soon_excludes_done_and_cancelled():
    tasks = [_task(date(2026, 1, 1), status_token="x"), _task(date(2026, 1, 1), status_token="-")]
    assert remind.due_soon_tasks(tasks, today=date(2026, 1, 5)) == []


def test_format_reminder_marks_overdue():
    tasks = [_task(date(2026, 1, 1), status_token=" ")]
    text = remind.format_reminder(tasks, today=date(2026, 1, 5))
    assert "期限超過" in text
    assert "Task" in text


def test_format_reminder_does_not_mark_future_due():
    tasks = [_task(date(2026, 1, 10))]
    text = remind.format_reminder(tasks, today=date(2026, 1, 5))
    assert "期限超過" not in text


def test_send_reminder_calls_notify_when_due_tasks_exist(fake_notify):
    tasks = [_task(date(2026, 1, 1))]
    result = remind.send_reminder(tasks, today=date(2026, 1, 5))
    assert result == {}
    assert len(fake_notify.calls) == 1
    assert "Task" in fake_notify.calls[0][0]


def test_send_reminder_does_nothing_when_no_due_tasks(fake_notify):
    tasks = [_task(date(2026, 6, 1))]
    result = remind.send_reminder(tasks, today=date(2026, 1, 5))
    assert result is None
    assert fake_notify.calls == []


def test_send_reminder_default_channel_is_desktop(fake_notify):
    tasks = [_task(date(2026, 1, 1))]
    remind.send_reminder(tasks, today=date(2026, 1, 5))
    assert fake_notify.calls[0][1] == ["desktop"]


def test_send_reminder_custom_channels(fake_notify):
    tasks = [_task(date(2026, 1, 1))]
    remind.send_reminder(tasks, channels=["discord"], today=date(2026, 1, 5))
    assert fake_notify.calls[0][1] == ["discord"]
