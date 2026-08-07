from __future__ import annotations

import subprocess

import pytest

from claude_bridge.config import Project, Secrets, Settings


@pytest.fixture
def settings(tmp_path):
    proj_dir = tmp_path / "hobby"
    proj_dir.mkdir()
    other_dir = tmp_path / "myapp"
    other_dir.mkdir()
    return Settings(
        projects=[
            Project(alias="hobby", path=proj_dir),
            Project(alias="myapp", path=other_dir),
        ],
        default_project="hobby",
        default_mode="diff",
        timeout_seconds=1800,
        progress_interval_seconds=20,
        heartbeat_enabled=False,
        heartbeat_interval_seconds=3600,
    )


@pytest.fixture
def secrets():
    return Secrets(bot_token="bot-token", channel_id="555555", allowed_user_ids=frozenset({"111"}))


@pytest.fixture
def no_sleep(monkeypatch):
    """Replace reqretry's time.sleep so retry backoff doesn't actually wait."""
    waits = []
    monkeypatch.setattr("reqretry.session.time.sleep", lambda seconds: waits.append(seconds))
    return waits


@pytest.fixture
def git_repo(tmp_path):
    """A minimal git repo with one commit, ready for `git diff HEAD` tests."""
    repo = tmp_path / "repo"
    repo.mkdir()
    run = lambda *args: subprocess.run(  # noqa: E731
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )
    run("init", "-q")
    run("config", "user.email", "test@example.com")
    run("config", "user.name", "Test")
    (repo / "a.txt").write_text("hello\n", encoding="utf-8")
    run("add", "a.txt")
    run("commit", "-q", "-m", "initial")
    return repo
