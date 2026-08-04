from __future__ import annotations

import responses
from typer.testing import CliRunner

from translate_comments.cli import app
from translate_comments.deepl_client import DEEPL_PRO_URL

runner = CliRunner()


def _mock_translate(*texts_per_call):
    """Register one DeepL response per call, each echoing back `TR: <original>`."""
    for texts in texts_per_call:
        responses.add(
            responses.POST,
            DEEPL_PRO_URL,
            json={"translations": [{"text": f"TR: {t}"} for t in texts]},
            status=200,
        )


# --- validation / early exits --------------------------------------------------------


def test_not_found_path_fails(tmp_path):
    result = runner.invoke(app, [str(tmp_path / "missing.py"), "--from", "ja", "--to", "en"])

    assert result.exit_code == 1
    assert "Not found" in result.output


def test_no_translatable_comments_reports_and_exits_cleanly(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")

    result = runner.invoke(app, [str(tmp_path), "--from", "ja", "--to", "en"])

    assert result.exit_code == 0, result.output
    assert "No translatable comments found" in result.output


def test_unsupported_from_language_fails(tmp_path):
    (tmp_path / "a.py").write_text("# hello\n", encoding="utf-8")

    result = runner.invoke(app, [str(tmp_path), "--from", "de", "--to", "en"])

    assert result.exit_code == 1
    assert "Unsupported --from" in result.output


def test_unsupported_to_language_fails(tmp_path):
    (tmp_path / "a.py").write_text("# hello\n", encoding="utf-8")

    result = runner.invoke(app, [str(tmp_path), "--from", "ja", "--to", "de"])

    assert result.exit_code == 1
    assert "Unsupported --to" in result.output


def test_from_equals_only_to_fails(tmp_path):
    (tmp_path / "a.py").write_text("# hello\n", encoding="utf-8")

    result = runner.invoke(app, [str(tmp_path), "--from", "ja", "--to", "ja"])

    assert result.exit_code == 1
    assert "--to" in result.output


def test_unsupported_single_file_fails(tmp_path):
    f = tmp_path / "data.json"
    f.write_text("{}\n", encoding="utf-8")

    result = runner.invoke(app, [str(f), "--from", "ja", "--to", "en"])

    assert result.exit_code == 1
    assert "Unsupported" in result.output


def test_missing_api_key_fails_with_clear_error(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPL_API_KEY", raising=False)
    (tmp_path / "a.py").write_text("# hello\n", encoding="utf-8")

    result = runner.invoke(app, [str(tmp_path), "--from", "ja", "--to", "en", "--yes"])

    assert result.exit_code == 1
    assert "DEEPL_API_KEY" in result.output


# --- dry-run / confirmation -----------------------------------------------------------


@responses.activate
def test_dry_run_shows_preview_and_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPL_API_KEY", "test-key")
    original = "# hello\nx = 1\n"
    f = tmp_path / "a.py"
    f.write_text(original, encoding="utf-8")

    result = runner.invoke(app, [str(tmp_path), "--from", "ja", "--to", "en", "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "hello" in result.output
    assert "dry run" in result.output
    assert f.read_text(encoding="utf-8") == original
    assert len(responses.calls) == 0


@responses.activate
def test_confirmation_declined_aborts(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPL_API_KEY", "test-key")
    original = "# hello\nx = 1\n"
    f = tmp_path / "a.py"
    f.write_text(original, encoding="utf-8")

    result = runner.invoke(app, [str(tmp_path), "--from", "ja", "--to", "en"], input="n\n")

    assert result.exit_code == 1
    assert "Aborted" in result.output
    assert f.read_text(encoding="utf-8") == original
    assert len(responses.calls) == 0


# --- inline mode ------------------------------------------------------------------


@responses.activate
def test_yes_flag_translates_inline_and_writes_file(tmp_path, monkeypatch, no_sleep):
    monkeypatch.setenv("DEEPL_API_KEY", "test-key")
    f = tmp_path / "a.py"
    f.write_text("# hello\nx = 1\n", encoding="utf-8")
    _mock_translate(["hello"])

    result = runner.invoke(app, [str(tmp_path), "--from", "ja", "--to", "en", "--yes"])

    assert result.exit_code == 0, result.output
    assert f.read_text(encoding="utf-8") == "# hello\n# [EN] TR: hello\nx = 1\n"


# --- separate mode ------------------------------------------------------------------


@responses.activate
def test_separate_mode_writes_per_language_files_and_leaves_original(tmp_path, monkeypatch, no_sleep):
    monkeypatch.setenv("DEEPL_API_KEY", "test-key")
    original = "# hello\nx = 1\n"
    f = tmp_path / "a.py"
    f.write_text(original, encoding="utf-8")
    _mock_translate(["hello"], ["hello"])

    result = runner.invoke(
        app, [str(tmp_path), "--from", "ja", "--to", "en,fr", "--mode", "separate", "--yes"]
    )

    assert result.exit_code == 0, result.output
    assert f.read_text(encoding="utf-8") == original
    assert (tmp_path / "a_en.py").read_text(encoding="utf-8") == "# TR: hello\nx = 1\n"
    assert (tmp_path / "a_fr.py").read_text(encoding="utf-8") == "# TR: hello\nx = 1\n"


# --- replace mode ------------------------------------------------------------------


@responses.activate
def test_replace_mode_overwrites_original_file_in_place(tmp_path, monkeypatch, no_sleep):
    monkeypatch.setenv("DEEPL_API_KEY", "test-key")
    f = tmp_path / "a.py"
    f.write_text("# hello\nx = 1\n", encoding="utf-8")
    _mock_translate(["hello"])

    result = runner.invoke(
        app, [str(tmp_path), "--from", "ja", "--to", "en", "--mode", "replace", "--yes"]
    )

    assert result.exit_code == 0, result.output
    assert "overwrite the original comments" in result.output
    assert f.read_text(encoding="utf-8") == "# TR: hello\nx = 1\n"
    assert not (tmp_path / "a_en.py").exists()


def test_replace_mode_rejects_multiple_target_languages(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPL_API_KEY", "test-key")
    (tmp_path / "a.py").write_text("# hello\n", encoding="utf-8")

    result = runner.invoke(
        app, [str(tmp_path), "--from", "ja", "--to", "en,fr", "--mode", "replace", "--yes"]
    )

    assert result.exit_code == 1
    assert "single" in result.output


# --- recursive / non-recursive --------------------------------------------------------


@responses.activate
def test_recursive_processes_subdirectory(tmp_path, monkeypatch, no_sleep):
    monkeypatch.setenv("DEEPL_API_KEY", "test-key")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "a.py").write_text("# nested\n", encoding="utf-8")
    _mock_translate(["nested"])

    result = runner.invoke(
        app, [str(tmp_path), "--from", "ja", "--to", "en", "--recursive", "--yes"]
    )

    assert result.exit_code == 0, result.output
    assert (sub / "a.py").read_text(encoding="utf-8") == "# nested\n# [EN] TR: nested\n"


def test_non_recursive_ignores_subdirectory(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPL_API_KEY", "test-key")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "a.py").write_text("# nested\n", encoding="utf-8")

    result = runner.invoke(app, [str(tmp_path), "--from", "ja", "--to", "en"])

    assert result.exit_code == 0, result.output
    assert "No translatable comments found" in result.output
