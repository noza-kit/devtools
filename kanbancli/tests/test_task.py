from datetime import date

import pytest

from kanbancli.task import STATUS_TOKENS, Task, TaskParseError, format_line, generate_id, parse_line, resolve_status_token


def test_parse_full_line():
    line = "- [~] データベースのテーブル設計 [!!] @add:2026-08-01 @due:2026-08-10 #database id:x7a9"
    t = parse_line(line)
    assert t.id == "x7a9"
    assert t.content == "データベースのテーブル設計"
    assert t.status_token == "~"
    assert t.priority == 2
    assert t.add_date == date(2026, 8, 1)
    assert t.due_date == date(2026, 8, 10)
    assert t.tags == ["database"]
    assert t.level == 0


def test_parse_progress_token():
    t = parse_line("- [iii] 外部APIの調査 [!] @add:2026-08-06 id:a1b2")
    assert t.status_token == "iii"
    assert t.category == "progress"
    assert t.percent == 30


def test_parse_indented_subtask_level():
    t = parse_line("  - [x] APIキーの取得 id:c3d4")
    assert t.level == 1
    assert t.category == "done"


def test_parse_uses_fixed_two_space_unit():
    # kanbancli always divides indent width by 2 to get level -- a file
    # consistently using 4 spaces per level still nests correctly (each
    # deeper line gets a strictly larger level number), just with level
    # numbers double what a 4-space-per-level author might expect; see
    # README's "Subtask indentation" section.
    assert parse_line("  - [ ] two spaces id:aaaa").level == 1
    assert parse_line("    - [ ] four spaces id:bbbb").level == 2


def test_parse_tabs_are_expanded_before_measuring_indent():
    t = parse_line("\t- [ ] tab-indented id:cccc")
    assert t.level == 2  # a tab expands to 4 spaces (expandtabs default), i.e. two 2-space levels


def test_parse_multiple_depends():
    t = parse_line("- [ ] バックエンドの実装 [!!!] @depends:x7a9 @depends:a1b2 id:g7h8")
    assert t.depends == ["x7a9", "a1b2"]
    assert t.priority == 3


def test_parse_no_id_raises():
    with pytest.raises(TaskParseError):
        parse_line("- [ ] no id here")


def test_parse_non_task_line_returns_none():
    assert parse_line("# just a heading, not a task") is None
    assert parse_line("") is None


def test_format_line_round_trip():
    original = parse_line("- [~] Task content [!!] @add:2026-08-01 @due:2026-08-10 #database id:x7a9")
    reparsed = parse_line(format_line(original))
    assert reparsed == original


def test_format_line_subtask_indent():
    t = Task(id="abcd", content="child", status_token=" ", level=1)
    assert format_line(t).startswith("  - [ ]")


def test_format_line_omits_absent_optional_fields():
    t = Task(id="abcd", content="minimal task", status_token=" ")
    line = format_line(t)
    assert "@due" not in line
    assert "@recur" not in line
    assert "#" not in line
    assert line == "- [ ] minimal task id:abcd"


def test_all_status_tokens_have_a_category():
    for token in (" ", "~", "/", "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "-", ">"):
        assert token in STATUS_TOKENS


def test_resolve_status_token_raw():
    assert resolve_status_token("x") == "x"


def test_resolve_status_token_alias():
    assert resolve_status_token("done") == "x"
    assert resolve_status_token("30") == "iii"


def test_resolve_status_token_unknown_raises():
    with pytest.raises(TaskParseError):
        resolve_status_token("bogus")


def test_generate_id_length_and_charset():
    tid = generate_id(set())
    assert len(tid) == 4
    assert tid.isalnum()
    assert tid.islower() or tid.isdigit() or tid.isalnum()


def test_generate_id_avoids_collisions():
    existing = {"aaaa"}
    for _ in range(50):
        assert generate_id(existing) not in existing
