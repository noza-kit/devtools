from __future__ import annotations

from claude_bridge.message_parse import parse_directives


def test_parses_project_and_mode_directives():
    parsed = parse_directives("READMEを直して\nproject: hobby\nmode: summary")
    assert parsed.instruction == "READMEを直して"
    assert parsed.project_alias == "hobby"
    assert parsed.mode == "summary"


def test_no_directives_leaves_instruction_untouched():
    parsed = parse_directives("READMEを直して")
    assert parsed.instruction == "READMEを直して"
    assert parsed.project_alias is None
    assert parsed.mode is None


def test_directive_only_message_yields_empty_instruction():
    parsed = parse_directives("project: hobby")
    assert parsed.instruction == ""
    assert parsed.project_alias == "hobby"


def test_case_insensitive_and_extra_whitespace():
    parsed = parse_directives("do it\nProject:   hobby  \nMODE: diff")
    assert parsed.project_alias == "hobby"
    assert parsed.mode == "diff"


def test_invalid_mode_value_is_not_matched():
    parsed = parse_directives("do it\nmode: nonsense")
    assert parsed.mode is None
    # not a recognized directive line, so it's left in the instruction
    assert "mode: nonsense" in parsed.instruction
