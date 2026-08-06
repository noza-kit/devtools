from __future__ import annotations

import subprocess

import pytest


class FakeCompletedProcess:
    def __init__(self, stdout: str = "", returncode: int = 0):
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


@pytest.fixture
def fake_subprocess_run(monkeypatch):
    """subprocess.run をモックし、コマンド名 -> stdout のマップで応答する。

    使い方: fake_subprocess_run({"fd": "a.txt\\n", "rg": "b.txt\\n"})
    戻り値は呼び出されたコマンド一覧(list[list[str]])を記録するリスト。
    """
    calls: list[list[str]] = []

    def _install(responses: dict[str, str], returncodes: dict[str, int] | None = None):
        returncodes = returncodes or {}

        def _fake_run(cmd, *args, **kwargs):
            calls.append(cmd)
            name = cmd[0]
            stdout = responses.get(name, "")
            returncode = returncodes.get(name, 0)
            return FakeCompletedProcess(stdout=stdout, returncode=returncode)

        monkeypatch.setattr(subprocess, "run", _fake_run)
        return calls

    return _install
