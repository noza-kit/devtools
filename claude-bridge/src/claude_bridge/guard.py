from __future__ import annotations

import re

# Each pattern matches one well-known hard-to-reverse command. Matched
# case-insensitively against the raw instruction text (not Claude's actual
# tool calls -- this is a pre-flight heuristic on what the *user asked for*,
# not a sandbox around what Claude *does*).
_DANGEROUS_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("git push --force", re.compile(r"git\s+push\b[^\n]*(--force(-with-lease)?\b|\s-f\b)")),
    ("git push --delete (remote branch削除)", re.compile(r"git\s+push\b[^\n]*--delete\b")),
    ("git reset --hard", re.compile(r"git\s+reset\b[^\n]*--hard\b")),
    ("git clean -f", re.compile(r"git\s+clean\b[^\n]*-\w*f")),
    ("git branch -D", re.compile(r"git\s+branch\b[^\n]*-D\b")),
    ("rm -rf / rm -fr", re.compile(r"\brm\s+-\w*r\w*f\b|\brm\s+-\w*f\w*r\b")),
    ("del /s /q", re.compile(r"\bdel\s+.*\/s\b", re.IGNORECASE)),
    ("rd /s", re.compile(r"\brd\s+.*\/s\b", re.IGNORECASE)),
    ("Remove-Item -Recurse -Force", re.compile(r"remove-item\b(?=[^\n]*-recurse)(?=[^\n]*-force)", re.IGNORECASE)),
    ("DROP TABLE/DATABASE/SCHEMA", re.compile(r"\bdrop\s+(table|database|schema)\b", re.IGNORECASE)),
    ("TRUNCATE TABLE", re.compile(r"\btruncate\s+table\b", re.IGNORECASE)),
    ("ディスクフォーマット", re.compile(r"\bformat\s+[a-z]:", re.IGNORECASE)),
    ("terraform destroy", re.compile(r"\bterraform\s+destroy\b")),
    ("docker prune -f", re.compile(r"\bdocker\s+\w+\s+prune\b[^\n]*-f\b")),
    ("kubectl delete", re.compile(r"\bkubectl\s+delete\b")),
]


def detect_dangerous(instruction: str) -> list[str]:
    """Return the human-readable labels of every dangerous-operation pattern
    matched in `instruction`. Empty if none matched (safe to run without a
    Discord confirmation round-trip)."""
    return [label for label, pattern in _DANGEROUS_PATTERNS if pattern.search(instruction)]
