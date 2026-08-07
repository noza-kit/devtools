from __future__ import annotations

from claude_bridge.routing import IncomingMessage, PendingConfirmation, decide

CHANNEL = "555555"
USER = "111"
OTHER_USER = "999"


def _msg(content, *, author_id=USER, channel_id=CHANNEL, message_id="1"):
    return IncomingMessage(author_id=author_id, channel_id=channel_id, message_id=message_id, content=content)


def _decide(settings, content, **kwargs):
    defaults = dict(
        allowed_channel_id=CHANNEL,
        allowed_user_ids=frozenset({USER}),
        pending=None,
        has_running_task=False,
        is_paused=False,
    )
    defaults.update(kwargs)
    return decide(_msg(content), settings, **defaults)


def test_wrong_channel_is_ignored(settings):
    decision = decide(
        _msg("do something", channel_id="000"),
        settings,
        allowed_channel_id=CHANNEL,
        allowed_user_ids=frozenset({USER}),
        pending=None,
        has_running_task=False,
        is_paused=False,
    )
    assert decision.kind == "ignore"


def test_unauthorized_user_is_ignored(settings):
    decision = decide(
        _msg("do something", author_id=OTHER_USER),
        settings,
        allowed_channel_id=CHANNEL,
        allowed_user_ids=frozenset({USER}),
        pending=None,
        has_running_task=False,
        is_paused=False,
    )
    assert decision.kind == "ignore"


def test_plain_instruction_runs_with_defaults(settings):
    decision = _decide(settings, "READMEを直して")
    assert decision.kind == "run"
    assert decision.project_alias == "hobby"
    assert decision.mode == "diff"
    assert decision.instruction == "READMEを直して"


def test_project_directive_selects_project(settings):
    decision = _decide(settings, "READMEを直して\nproject: myapp")
    assert decision.kind == "run"
    assert decision.project_alias == "myapp"


def test_unknown_project_alias_is_rejected(settings):
    decision = _decide(settings, "do it\nproject: nonexistent")
    assert decision.kind == "unknown_project"
    assert decision.reply is not None


def test_empty_instruction_after_stripping_directives_is_ignored(settings):
    decision = _decide(settings, "project: hobby")
    assert decision.kind == "ignore"


def test_dangerous_instruction_awaits_confirmation(settings):
    decision = _decide(settings, "git push --force origin main")
    assert decision.kind == "await_confirmation"
    assert decision.pending is not None
    assert decision.pending.instruction == "git push --force origin main"


def test_confirmation_yes_runs_pending(settings):
    pending = PendingConfirmation(
        project_alias="hobby", mode="diff", instruction="git push --force", reasons=["git push --force"]
    )
    decision = decide(
        _msg("yes"),
        settings,
        allowed_channel_id=CHANNEL,
        allowed_user_ids=frozenset({USER}),
        pending=pending,
        has_running_task=False,
        is_paused=False,
    )
    assert decision.kind == "run"
    assert decision.instruction == "git push --force"


def test_confirmation_declined_on_anything_else(settings):
    pending = PendingConfirmation(
        project_alias="hobby", mode="diff", instruction="git push --force", reasons=["git push --force"]
    )
    decision = decide(
        _msg("actually never mind"),
        settings,
        allowed_channel_id=CHANNEL,
        allowed_user_ids=frozenset({USER}),
        pending=pending,
        has_running_task=False,
        is_paused=False,
    )
    assert decision.kind == "confirmation_declined"


def test_stop_cancels_running_task(settings):
    decision = _decide(settings, "stop", has_running_task=True)
    assert decision.kind == "cancel"


def test_stop_with_no_running_task_is_ignored(settings):
    decision = _decide(settings, "stop", has_running_task=False)
    assert decision.kind == "ignore"


# -- pause / resume --------------------------------------------------------------


def test_pause_word_pauses(settings):
    decision = _decide(settings, "終了")
    assert decision.kind == "pause"
    assert decision.reply is not None


def test_pause_english_synonym(settings):
    for word in ("shutdown", "exit", "SHUTDOWN"):
        assert _decide(settings, word).kind == "pause"


def test_pause_while_already_paused_is_a_notice(settings):
    decision = _decide(settings, "終了", is_paused=True)
    assert decision.kind == "notice"


def test_resume_word_resumes_when_paused(settings):
    decision = _decide(settings, "起動", is_paused=True)
    assert decision.kind == "resume"


def test_resume_while_not_paused_is_a_notice(settings):
    decision = _decide(settings, "起動", is_paused=False)
    assert decision.kind == "notice"


def test_regular_instruction_while_paused_is_a_notice_not_run(settings):
    decision = _decide(settings, "READMEを直して", is_paused=True)
    assert decision.kind == "notice"
    assert decision.reply is not None


def test_stop_while_paused_is_a_notice_not_cancel(settings):
    # `stop` cancels a running task, but while paused nothing normal runs;
    # the paused-gate should catch it before the stop-word check.
    decision = _decide(settings, "stop", is_paused=True, has_running_task=True)
    assert decision.kind == "notice"


def test_usage_word_returns_usage_decision(settings):
    for word in ("usage", "使用量", "cost", "コスト"):
        assert _decide(settings, word).kind == "usage"


def test_usage_works_while_paused(settings):
    decision = _decide(settings, "usage", is_paused=True)
    assert decision.kind == "usage"


def test_usage_ignores_a_normal_sentence_containing_the_word(settings):
    # exact-match only, like the other control words -- avoids misfiring on
    # a real instruction that happens to mention "usage"/"コスト".
    decision = _decide(settings, "コストを削減する関数を書いて")
    assert decision.kind == "run"


def test_pending_confirmation_takes_priority_over_paused_gate(settings):
    pending = PendingConfirmation(
        project_alias="hobby", mode="diff", instruction="git push --force", reasons=["git push --force"]
    )
    decision = decide(
        _msg("yes"),
        settings,
        allowed_channel_id=CHANNEL,
        allowed_user_ids=frozenset({USER}),
        pending=pending,
        has_running_task=False,
        is_paused=True,
    )
    assert decision.kind == "run"
