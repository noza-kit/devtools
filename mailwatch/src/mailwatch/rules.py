from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from mailwatch.message import ParsedMessage

DEFAULT_GMAIL_QUERY = "in:inbox newer_than:1d"
DEFAULT_POLL_INTERVAL_SECONDS = 300
DEFAULT_ATTACHMENT_DIR = "./attachments"


class RuleConfigError(Exception):
    pass


@dataclass
class Rule:
    """One watch rule. All specified conditions must match (AND); each
    `*_contains` list matches if any of its keywords is found (OR)."""

    name: str
    channels: list[str]
    from_contains: Optional[str] = None
    subject_contains: list[str] = field(default_factory=list)
    body_contains: list[str] = field(default_factory=list)
    save_attachments: bool = False
    attachment_dir: str = DEFAULT_ATTACHMENT_DIR

    def matches(self, message: ParsedMessage) -> bool:
        if self.from_contains and self.from_contains.lower() not in message.from_header.lower():
            return False
        if self.subject_contains and not any(kw.lower() in message.subject.lower() for kw in self.subject_contains):
            return False
        if self.body_contains and not any(kw.lower() in message.body_text.lower() for kw in self.body_contains):
            return False
        return True


@dataclass
class WatchConfig:
    rules: list[Rule]
    gmail_query: str
    poll_interval_seconds: int
    notify_config: dict[str, Any]


def load_rules_config(path: Path) -> WatchConfig:
    """Load and validate a mailwatch rules YAML file. See mailwatch/README.md
    for the full schema."""
    text = path.read_text(encoding="utf-8")
    try:
        raw = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise RuleConfigError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise RuleConfigError(f"Config file must contain a top-level mapping: {path}")

    rules_raw = raw.get("rules") or []
    if not rules_raw:
        raise RuleConfigError(f"No rules defined in {path} (expected a top-level 'rules' list)")

    attachments_raw = raw.get("attachments") or {}
    default_save = bool(attachments_raw.get("enabled", False))
    default_dir = str(attachments_raw.get("save_dir", DEFAULT_ATTACHMENT_DIR))

    rules: list[Rule] = []
    seen_names: set[str] = set()
    for i, r in enumerate(rules_raw):
        if not isinstance(r, dict):
            raise RuleConfigError(f"rules[{i}] must be a mapping, got {type(r).__name__}")

        name = str(r.get("name") or f"rule-{i + 1}")
        if name in seen_names:
            raise RuleConfigError(f"Duplicate rule name: {name!r}")
        seen_names.add(name)

        channels = r.get("channels") or []
        if not channels:
            raise RuleConfigError(f"Rule {name!r} has no 'channels' configured")

        rule = Rule(
            name=name,
            channels=[str(c) for c in channels],
            from_contains=(str(r["from"]) if r.get("from") else None),
            subject_contains=[str(kw) for kw in (r.get("subject_contains") or [])],
            body_contains=[str(kw) for kw in (r.get("body_contains") or [])],
            save_attachments=bool(r.get("save_attachments", default_save)),
            attachment_dir=str(r.get("attachment_dir") or default_dir),
        )
        if not (rule.from_contains or rule.subject_contains or rule.body_contains):
            raise RuleConfigError(
                f"Rule {name!r} has no matching conditions (from/subject_contains/body_contains)"
            )
        rules.append(rule)

    gmail_raw = raw.get("gmail") or {}

    return WatchConfig(
        rules=rules,
        gmail_query=str(gmail_raw.get("query", DEFAULT_GMAIL_QUERY)),
        poll_interval_seconds=int(raw.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS)),
        notify_config=dict(raw.get("notify") or {}),
    )
