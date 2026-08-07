from __future__ import annotations

from claude_bridge import diff_view


def test_capture_diff_empty_when_no_changes(git_repo):
    assert diff_view.capture_diff(git_repo) == ""


def test_capture_diff_shows_modification(git_repo):
    (git_repo / "a.txt").write_text("hello\nworld\n", encoding="utf-8")
    diff_text = diff_view.capture_diff(git_repo)
    assert "world" in diff_text
    assert "a.txt" in diff_text


def test_capture_diff_non_git_dir_returns_empty(tmp_path):
    not_a_repo = tmp_path / "plain"
    not_a_repo.mkdir()
    assert diff_view.capture_diff(not_a_repo) == ""


def test_changed_files_lists_modified_paths(git_repo):
    (git_repo / "a.txt").write_text("changed\n", encoding="utf-8")
    (git_repo / "b.txt").write_text("new\n", encoding="utf-8")
    import subprocess

    subprocess.run(["git", "add", "b.txt"], cwd=git_repo, check=True, capture_output=True)
    files = diff_view.changed_files(git_repo)
    assert set(files) == {"a.txt", "b.txt"}


def test_render_diff_no_changes_message():
    presentation = diff_view.render_diff("")
    assert presentation.messages == ["変更はありませんでした。"]
    assert presentation.attachment is None


def test_render_diff_small_diff_fits_one_chunk():
    diff_text = "diff --git a/x b/x\n+added line\n"
    presentation = diff_view.render_diff(diff_text)
    assert len(presentation.messages) == 1
    assert presentation.messages[0].startswith("```diff\n")
    assert presentation.attachment is None


def test_render_diff_large_diff_falls_back_to_attachment():
    # Each line ~30 chars; with a small max_length, force many chunks.
    diff_text = "".join(f"+line number {i}\n" for i in range(500))
    presentation = diff_view.render_diff(diff_text, max_length=200)
    assert presentation.attachment is not None
    assert presentation.attachment.decode("utf-8") == diff_text
    assert presentation.attachment_name == "changes.diff"


def test_render_diff_respects_message_length_budget():
    diff_text = "".join(f"+line {i}\n" for i in range(50))
    presentation = diff_view.render_diff(diff_text, max_length=200)
    if presentation.attachment is None:
        for msg in presentation.messages:
            assert len(msg) <= 200


def test_render_summary_with_claude_text_and_files():
    text = diff_view.render_summary(["a.py", "b.py"], "READMEを更新しました。")
    assert "READMEを更新しました。" in text
    assert "a.py" in text
    assert "b.py" in text
    assert "2件" in text


def test_render_summary_no_changes():
    assert diff_view.render_summary([], None) == "変更はありませんでした。"
