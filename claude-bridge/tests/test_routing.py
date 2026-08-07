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
    )
    assert decision.kind == "confirmation_declined"


def test_stop_cancels_running_task(settings):
    decision = _decide(settings, "stop", has_running_task=True)
    assert decision.kind == "cancel"


def test_stop_with_no_running_task_is_ignored(settings):
    decision = _decide(settings, "stop", has_running_task=False)
    assert decision.kind == "ignore"
