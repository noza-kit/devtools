from __future__ import annotations

import pytest

from mailwatch.message import ParsedMessage
from mailwatch.rules import Rule, RuleConfigError, load_rules_config


def _message(**overrides) -> ParsedMessage:
    defaults = dict(
        id="msg1",
        thread_id="t1",
        from_header="Boss <boss@example.com>",
        subject="至急: 先月分の請求書",
        date_header="Mon, 1 Jan 2024 09:00:00 +0900",
        internal_date_ms=1704067200000,
        body_text="添付の請求書番号をご確認ください。",
    )
    defaults.update(overrides)
    return ParsedMessage(**defaults)


def test_rule_matches_from_substring():
    rule = Rule(name="r", channels=["slack"], from_contains="boss@example.com")
    assert rule.matches(_message())
    assert not rule.matches(_message(from_header="someone@else.com"))


def test_rule_matches_from_is_case_insensitive():
    rule = Rule(name="r", channels=["slack"], from_contains="BOSS@EXAMPLE.COM")
    assert rule.matches(_message())


def test_rule_subject_contains_is_or():
    rule = Rule(name="r", channels=["slack"], subject_contains=["至急", "見積書"])
    assert rule.matches(_message())
    assert not rule.matches(_message(subject="定例会議のお知らせ"))


def test_rule_body_contains_matches():
    rule = Rule(name="r", channels=["slack"], body_contains=["請求書番号"])
    assert rule.matches(_message())
    assert not rule.matches(_message(body_text="特に用件はありません"))


def test_rule_all_conditions_are_anded():
    rule = Rule(name="r", channels=["slack"], from_contains="boss@example.com", subject_contains=["見積書"])
    # from matches but subject doesn't -> no match
    assert not rule.matches(_message())


def test_load_rules_config(tmp_path):
    path = tmp_path / "rules.yaml"
    path.write_text(
        """
poll_interval_seconds: 60
gmail:
  query: "in:inbox newer_than:2d"
rules:
  - name: boss-urgent
    from: "boss@example.com"
    subject_contains: ["至急"]
    channels: ["slack"]
    save_attachments: true
    attachment_dir: "./out"
  - name: invoices
    body_contains: ["請求書番号"]
    channels: ["discord"]
notify:
  slack_webhook_url: "https://hooks.slack.com/services/xxx"
""",
        encoding="utf-8",
    )

    config = load_rules_config(path)

    assert config.poll_interval_seconds == 60
    assert config.gmail_query == "in:inbox newer_than:2d"
    assert len(config.rules) == 2
    assert config.rules[0].name == "boss-urgent"
    assert config.rules[0].save_attachments is True
    assert config.rules[0].attachment_dir == "./out"
    assert config.rules[1].save_attachments is False
    assert config.notify_config == {"slack_webhook_url": "https://hooks.slack.com/services/xxx"}


def test_load_rules_config_requires_rules(tmp_path):
    path = tmp_path / "rules.yaml"
    path.write_text("poll_interval_seconds: 60\n", encoding="utf-8")

    with pytest.raises(RuleConfigError, match="No rules defined"):
        load_rules_config(path)


def test_load_rules_config_requires_channels(tmp_path):
    path = tmp_path / "rules.yaml"
    path.write_text(
        "rules:\n  - name: r1\n    from: boss@example.com\n",
        encoding="utf-8",
    )

    with pytest.raises(RuleConfigError, match="no 'channels'"):
        load_rules_config(path)


def test_load_rules_config_requires_a_condition(tmp_path):
    path = tmp_path / "rules.yaml"
    path.write_text(
        "rules:\n  - name: r1\n    channels: [slack]\n",
        encoding="utf-8",
    )

    with pytest.raises(RuleConfigError, match="no matching conditions"):
        load_rules_config(path)


def test_load_rules_config_rejects_duplicate_names(tmp_path):
    path = tmp_path / "rules.yaml"
    path.write_text(
        "rules:\n"
        "  - name: r1\n    from: a@example.com\n    channels: [slack]\n"
        "  - name: r1\n    from: b@example.com\n    channels: [slack]\n",
        encoding="utf-8",
    )

    with pytest.raises(RuleConfigError, match="Duplicate rule name"):
        load_rules_config(path)


def test_load_rules_config_attachments_default_applies_to_rules(tmp_path):
    path = tmp_path / "rules.yaml"
    path.write_text(
        "attachments:\n  enabled: true\n  save_dir: './global'\n"
        "rules:\n  - name: r1\n    from: a@example.com\n    channels: [slack]\n",
        encoding="utf-8",
    )

    config = load_rules_config(path)

    assert config.rules[0].save_attachments is True
    assert config.rules[0].attachment_dir == "./global"
