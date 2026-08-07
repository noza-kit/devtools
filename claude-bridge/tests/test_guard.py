from __future__ import annotations

import pytest

from claude_bridge.guard import detect_dangerous


@pytest.mark.parametrize(
    "instruction",
    [
        "git push --force origin main",
        "git push -f origin feature",
        "please run git reset --hard HEAD~3",
        "git clean -fd",
        "git branch -D old-feature",
        "rm -rf node_modules",
        "rm -fr build",
        "del /s /q C:\\temp\\*",
        "Remove-Item -Recurse -Force C:\\old",
        "DROP TABLE users;",
        "please DROP DATABASE prod",
        "TRUNCATE TABLE logs",
        "terraform destroy",
        "docker system prune -f",
        "kubectl delete deployment web",
    ],
)
def test_detects_dangerous_operations(instruction):
    assert detect_dangerous(instruction) != []


@pytest.mark.parametrize(
    "instruction",
    [
        "READMEにインストール手順を追記して",
        "テストを追加して",
        "git push origin feature-branch",
        "git status を確認して",
        "rm old_notes.txt",  # single-file rm, not -rf
        "新しい関数 format_date を追加して",
    ],
)
def test_safe_instructions_not_flagged(instruction):
    assert detect_dangerous(instruction) == []
