from __future__ import annotations

import sqlite3

import pytest

from claude_bridge.history_db import HistoryDB


@pytest.fixture
def db(tmp_path):
    database = HistoryDB(tmp_path / "history.db")
    yield database
    database.close()


def _finish_with_usage(db, run_id, *, cost, input_tokens=10, output_tokens=5):
    db.finish_run(
        run_id,
        status="completed",
        result_summary="done",
        session_id="sess",
        total_cost_usd=cost,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )


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


# -- usage -----------------------------------------------------------------


def test_finish_run_stores_usage_fields(db):
    run_id = db.start_run(project_alias="hobby", user_id="1", instruction="do it", mode="diff")
    _finish_with_usage(db, run_id, cost=0.05, input_tokens=200, output_tokens=80)

    run = db.get_run(run_id)
    assert run.total_cost_usd == 0.05
    assert run.input_tokens == 200
    assert run.output_tokens == 80


def test_usage_summary_empty_db_returns_zeros(db):
    summary = db.usage_summary()
    assert summary.run_count == 0
    assert summary.total_cost_usd == 0


def test_usage_summary_aggregates_across_runs(db):
    for cost in (0.01, 0.02, 0.03):
        run_id = db.start_run(project_alias="hobby", user_id="1", instruction="x", mode="diff")
        _finish_with_usage(db, run_id, cost=cost)

    summary = db.usage_summary()
    assert summary.run_count == 3
    assert summary.total_cost_usd == pytest.approx(0.06)


def test_usage_summary_running_run_has_no_cost_yet(db):
    db.start_run(project_alias="hobby", user_id="1", instruction="x", mode="diff")
    summary = db.usage_summary()
    assert summary.run_count == 1
    assert summary.total_cost_usd == 0


def test_usage_by_project_breaks_down_and_sorts_by_cost(db):
    run_a = db.start_run(project_alias="hobby", user_id="1", instruction="x", mode="diff")
    _finish_with_usage(db, run_a, cost=0.01)
    run_b = db.start_run(project_alias="myapp", user_id="1", instruction="x", mode="diff")
    _finish_with_usage(db, run_b, cost=0.10)

    by_project = db.usage_by_project()
    assert [p.project_alias for p in by_project] == ["myapp", "hobby"]
    assert by_project[0].total_cost_usd == pytest.approx(0.10)


def test_usage_summary_since_days_excludes_old_runs(db):
    run_id = db.start_run(project_alias="hobby", user_id="1", instruction="x", mode="diff")
    _finish_with_usage(db, run_id, cost=0.05)
    db._conn.execute("UPDATE runs SET started_at = datetime('now', '-30 days') WHERE id = ?", (run_id,))
    db._conn.commit()

    assert db.usage_summary(since_days=7).run_count == 0
    assert db.usage_summary().run_count == 1


def test_migration_adds_usage_columns_to_old_schema(tmp_path):
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_alias TEXT NOT NULL,
            user_id TEXT NOT NULL,
            instruction TEXT NOT NULL,
            mode TEXT NOT NULL,
            status TEXT NOT NULL,
            result_summary TEXT,
            session_id TEXT,
            started_at TEXT NOT NULL DEFAULT (datetime('now')),
            finished_at TEXT
        );
        CREATE TABLE sessions (
            project_alias TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    conn.execute(
        "INSERT INTO runs (project_alias, user_id, instruction, mode, status) VALUES (?, ?, ?, ?, ?)",
        ("hobby", "1", "old instruction", "diff", "completed"),
    )
    conn.commit()
    conn.close()

    with HistoryDB(path) as db:
        runs = db.recent_runs()
        assert len(runs) == 1
        assert runs[0].instruction == "old instruction"
        assert runs[0].total_cost_usd is None

        run_id = db.start_run(project_alias="hobby", user_id="1", instruction="new", mode="diff")
        _finish_with_usage(db, run_id, cost=0.02)
        assert db.usage_summary().total_cost_usd == pytest.approx(0.02)
