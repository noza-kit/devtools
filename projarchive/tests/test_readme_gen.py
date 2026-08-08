from __future__ import annotations

from projarchive import readme_gen


def test_ensure_readme_generates_when_missing(tmp_path):
    proj = tmp_path / "myproject"
    proj.mkdir()
    (proj / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (proj / "data").mkdir()

    path, generated = readme_gen.ensure_readme(proj)

    assert generated is True
    text = path.read_text(encoding="utf-8")
    assert "# myproject" in text
    assert "main.py" in text
    assert "data/" in text


def test_ensure_readme_leaves_existing_file_untouched(tmp_path):
    proj = tmp_path / "myproject"
    proj.mkdir()
    (proj / "README.md").write_text("original content\n", encoding="utf-8")

    path, generated = readme_gen.ensure_readme(proj)

    assert generated is False
    assert path.read_text(encoding="utf-8") == "original content\n"


def test_generate_readme_ignores_venv_and_git_dirs(tmp_path):
    proj = tmp_path / "myproject"
    (proj / ".venv").mkdir(parents=True)
    (proj / ".git").mkdir()
    (proj / "app.py").write_text("x", encoding="utf-8")

    text = readme_gen.generate_readme(proj)

    assert ".venv" not in text
    assert ".git" not in text
    assert "app.py" in text
