from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

import notesearch.cli as cli_module
from notesearch.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def fake_embedder_for_cli(monkeypatch):
    from conftest import FakeEmbedder

    monkeypatch.setattr(cli_module, "SentenceTransformerEmbedder", FakeEmbedder)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _config(tmp_path: Path, notes_dir: Path, db_dir: Path) -> Path:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        f"target_dirs:\n  - {notes_dir}\ndb_dir: {db_dir}\n",
        encoding="utf-8",
    )
    return cfg


def test_no_args_prints_help():
    result = runner.invoke(app, [])
    assert "Usage" in result.output  # Click's no_args_is_help; exit code 2 is its standard convention, not an error


def test_sync_command(tmp_path: Path):
    notes_dir = tmp_path / "notes"
    _write(notes_dir / "a.md", "some content")
    cfg = _config(tmp_path, notes_dir, tmp_path / "db")

    result = runner.invoke(app, ["sync", "--config", str(cfg)])
    assert result.exit_code == 0, result.output
    assert "1" in result.output  # "+1 追加" somewhere in the output


def test_clean_command(tmp_path: Path):
    notes_dir = tmp_path / "notes"
    note_path = notes_dir / "a.md"
    _write(note_path, "some content")
    cfg = _config(tmp_path, notes_dir, tmp_path / "db")

    runner.invoke(app, ["sync", "--config", str(cfg)])
    note_path.unlink()

    result = runner.invoke(app, ["clean", "--config", str(cfg)])
    assert result.exit_code == 0, result.output
    assert "1件" in result.output


def test_search_with_copy_flag(tmp_path: Path, monkeypatch):
    notes_dir = tmp_path / "notes"
    _write(notes_dir / "a.md", "Docker build cache troubleshooting guide")
    cfg = _config(tmp_path, notes_dir, tmp_path / "db")

    copied = {}
    monkeypatch.setattr("pyperclip.copy", lambda text: copied.setdefault("text", text))

    result = runner.invoke(app, ["Docker build cache", "--copy", "--config", str(cfg)])
    assert result.exit_code == 0, result.output
    assert "コピーしました" in result.output


def test_search_with_ask_flag_calls_gemini(tmp_path: Path, monkeypatch):
    notes_dir = tmp_path / "notes"
    _write(notes_dir / "a.md", "Docker build cache troubleshooting guide")
    cfg = _config(tmp_path, notes_dir, tmp_path / "db")

    monkeypatch.setattr(cli_module.gemini_mod, "ask", lambda prompt, api_key=None: "Gemini's answer text")

    result = runner.invoke(app, ["Docker build cache", "--ask", "--config", str(cfg)])
    assert result.exit_code == 0, result.output
    assert "Gemini's answer text" in result.output


def test_search_with_ask_flag_no_results(tmp_path: Path, monkeypatch):
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    cfg = _config(tmp_path, notes_dir, tmp_path / "db")

    called = []
    monkeypatch.setattr(cli_module.gemini_mod, "ask", lambda *a, **k: called.append(1))

    result = runner.invoke(app, ["anything", "--ask", "--config", str(cfg)])
    assert result.exit_code == 0, result.output
    assert called == []  # Gemini should not be called when there's nothing to answer from


def test_search_with_ask_flag_gemini_error_reported(tmp_path: Path, monkeypatch):
    from notesearch.gemini import GeminiError

    notes_dir = tmp_path / "notes"
    _write(notes_dir / "a.md", "some content")
    cfg = _config(tmp_path, notes_dir, tmp_path / "db")

    def raise_error(*a, **k):
        raise GeminiError("GEMINI_API_KEY is not set")

    monkeypatch.setattr(cli_module.gemini_mod, "ask", raise_error)

    result = runner.invoke(app, ["content", "--ask", "--config", str(cfg)])
    assert result.exit_code == 1
    assert "エラー" in result.output


def test_search_default_mode_invokes_tui(tmp_path: Path, monkeypatch):
    notes_dir = tmp_path / "notes"
    _write(notes_dir / "a.md", "some content")
    cfg = _config(tmp_path, notes_dir, tmp_path / "db")

    tui_calls = []
    monkeypatch.setattr("notesearch.tui.run_search_tui", lambda results, editor_command, console=None: tui_calls.append(results))

    result = runner.invoke(app, ["content", "--config", str(cfg)])
    assert result.exit_code == 0, result.output
    assert len(tui_calls) == 1


def test_search_missing_config_fails(tmp_path: Path):
    result = runner.invoke(app, ["query", "--config", str(tmp_path / "missing.yaml")])
    assert result.exit_code == 1


def test_search_dir_and_days_options_accepted(tmp_path: Path, monkeypatch):
    notes_dir = tmp_path / "notes"
    _write(notes_dir / "proj_a" / "note.md", "some content")
    cfg = _config(tmp_path, notes_dir, tmp_path / "db")

    monkeypatch.setattr("notesearch.tui.run_search_tui", lambda *a, **k: None)

    result = runner.invoke(app, ["content", "--dir", "proj_a", "--days", "30", "--config", str(cfg)])
    assert result.exit_code == 0, result.output
