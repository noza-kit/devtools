from __future__ import annotations

import sys
from pathlib import Path

import pytest


@pytest.fixture
def tunelab_home(monkeypatch, tmp_path):
    home = tmp_path / "tunelab_home"
    monkeypatch.setenv("TUNELAB_HOME", str(home))
    return home


@pytest.fixture
def quadratic_script(tmp_path):
    """A tiny standalone script: reads --x and --result-file, writes {"value": (x-3)**2}."""
    script = tmp_path / "quadratic.py"
    script.write_text(
        "import argparse, json\n"
        "parser = argparse.ArgumentParser()\n"
        "parser.add_argument('--x', type=float, required=True)\n"
        "parser.add_argument('--result-file', required=True)\n"
        "args = parser.parse_args()\n"
        "json.dump({'value': (args.x - 3.0) ** 2}, open(args.result_file, 'w'))\n",
        encoding="utf-8",
    )
    return script


@pytest.fixture
def quadratic_module(tmp_path, monkeypatch):
    """An importable module exposing objective(params) -> (x-3)**2, for callable-mode tests."""
    monkeypatch.syspath_prepend(str(tmp_path))
    module_path = tmp_path / "quadratic_objective.py"
    module_path.write_text(
        "def objective(params):\n"
        "    return (params['x'] - 3.0) ** 2\n"
        "\n"
        "def always_fails(params):\n"
        "    raise ValueError('boom')\n",
        encoding="utf-8",
    )
    sys.modules.pop("quadratic_objective", None)
    yield "quadratic_objective"
    sys.modules.pop("quadratic_objective", None)
