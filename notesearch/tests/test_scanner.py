from pathlib import Path

from notesearch.scanner import convert_pdfs, scan_files


def _touch(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_scan_files_finds_matching_extensions(tmp_path: Path):
    _touch(tmp_path / "a.md")
    _touch(tmp_path / "b.txt")
    _touch(tmp_path / "c.jpg")  # not in extensions
    result = scan_files([tmp_path], exclude=[], extensions=[".md", ".txt"])
    names = {p.name for p in result}
    assert names == {"a.md", "b.txt"}


def test_scan_files_recurses_into_subdirectories(tmp_path: Path):
    _touch(tmp_path / "sub" / "deep" / "note.md")
    result = scan_files([tmp_path], exclude=[], extensions=[".md"])
    assert len(result) == 1


def test_scan_files_respects_exclude(tmp_path: Path):
    _touch(tmp_path / "venv" / "lib" / "note.md")
    _touch(tmp_path / "real" / "note.md")
    result = scan_files([tmp_path], exclude=["venv"], extensions=[".md"])
    names = {str(p) for p in result}
    assert any("real" in n for n in names)
    assert not any("venv" in n for n in names)


def test_scan_files_extension_matching_is_case_insensitive(tmp_path: Path):
    _touch(tmp_path / "NOTE.MD")
    result = scan_files([tmp_path], exclude=[], extensions=[".md"])
    assert len(result) == 1


def test_scan_files_missing_target_dir_is_skipped_not_an_error(tmp_path: Path):
    result = scan_files([tmp_path / "does-not-exist"], exclude=[], extensions=[".md"])
    assert result == []


def test_scan_files_ignores_directories(tmp_path: Path):
    (tmp_path / "note.md").mkdir()  # a directory named "note.md", not a file
    result = scan_files([tmp_path], exclude=[], extensions=[".md"])
    assert result == []


def test_convert_pdfs_returns_empty_when_pdfcraft_not_installed(tmp_path: Path, monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pdfcraft.extract_md":
            raise ImportError("no pdfcraft")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    _touch(tmp_path / "doc.pdf")
    assert convert_pdfs([tmp_path], exclude=[]) == []


def test_convert_pdfs_skips_already_converted_up_to_date_md(tmp_path: Path, monkeypatch):
    import time

    pdf_path = tmp_path / "doc.pdf"
    _touch(pdf_path)
    md_path = tmp_path / "doc.md"
    time.sleep(0.01)
    _touch(md_path)  # newer than the pdf

    calls = []
    fake_module = type("FakeModule", (), {"extract_markdown": staticmethod(lambda p: calls.append(p) or "converted")})
    monkeypatch.setitem(__import__("sys").modules, "pdfcraft.extract_md", fake_module)

    result = convert_pdfs([tmp_path], exclude=[])
    assert result == [md_path]
    assert calls == []  # not re-converted, since .md is already newer
