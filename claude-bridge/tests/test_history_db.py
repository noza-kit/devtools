from __future__ import annotations

import pytest

from claude_bridge.history_db import HistoryDB


@pytest.fixture
def db(tmp_path):
    database = HistoryDB(tmp_path / "history.db")
    yield database
    database.close()


def test_start_and_finish_run_roundtrip(db):
    run_id = db.start_run(project_alias="hobby", user_id="1", instruction="do it", mode="diff")
    run = db.get_run(run_id)
    assert run.status == "running"
    assert run.instruction == "do it"

    db.finish_run(run_id, status="completed", result_summary="done", session_id="sess-1")
    run = db.get_run(run_id)
    assert run.status == "completed"
    assert run.result_summary == "done"
    assert run.session_id == "sess-1"
    assert run.finished_at is not None


def test_recent_runs_orders_newest_first(db):
    id1 = db.start_run(project_alias="hobby", user_id="1", instruction="first", mode="diff")
    id2 = db.start_run(project_alias="hobby", user_id="1", instruction="second", mode="diff")
    runs = db.recent_runs(limit=10)
    assert [r.id for r in runs][:2] == [id2, id1]


def test_session_id_roundtrip(db):
    assert db.get_session_id("hobby") is None
    db.set_session_id("hobby", "sess-1")
    assert db.get_session_id("hobby") == "sess-1"
    db.set_session_id("hobby", "sess-2")
    assert db.get_session_id("hobby") == "sess-2"


def test_clear_session_id(db):
    db.set_session_id("hobby", "sess-1")
    db.clear_session_id("hobby")
    assert db.get_session_id("hobby") is None


def test_session_ids_are_per_project(db):
    db.set_session_id("hobby", "sess-1")
    db.set_session_id("myapp", "sess-2")
    assert db.get_session_id("hobby") == "sess-1"
    assert db.get_session_id("myapp") == "sess-2"
