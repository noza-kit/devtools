from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from tunelab.config import ObjectiveSpec
from tunelab.objective.errors import ObjectiveError, TrialFailed


def _format_command(template: str, params: dict[str, Any], result_file: Path | None) -> str:
    fmt_values = dict(params)
    if result_file is not None:
        fmt_values["result_file"] = str(result_file)
    try:
        return template.format(**fmt_values)
    except KeyError as exc:
        raise ObjectiveError(f"command template references unknown placeholder {exc}") from exc


def run_command_objective(spec: ObjectiveSpec, params: dict[str, Any]) -> float:
    """Run the configured shell command for one trial and return its reported value.

    Literal `{`/`}` in `spec.command` must be doubled (`{{`/`}}`) since the
    template goes through `str.format`.
    """
    tmp_dir: str | None = None
    result_path: Path | None = None
    try:
        if spec.result_file:
            tmp_dir = tempfile.mkdtemp(prefix="tunelab-")
            result_path = Path(tmp_dir) / f"result.{spec.result_file}"

        command = _format_command(spec.command, params, result_path)
        env = {**os.environ, **spec.env}

        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(spec.working_dir),
                env=env,
                capture_output=True,
                text=True,
                timeout=spec.timeout_per_trial,
            )
        except subprocess.TimeoutExpired as exc:
            raise TrialFailed(f"command timed out after {spec.timeout_per_trial}s: {command}") from exc

        if proc.returncode != 0:
            raise TrialFailed(
                f"command exited with code {proc.returncode}: {command}\nstderr: {proc.stderr}",
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )

        if result_path is not None:
            if not result_path.exists():
                raise TrialFailed(f"result file {result_path} was not created by: {command}")
            try:
                data = json.loads(result_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise TrialFailed(f"result file {result_path} is not valid JSON: {exc}") from exc
            if "value" not in data:
                raise TrialFailed(f"result file {result_path} is missing the 'value' key")
            return float(data["value"])

        match = re.search(spec.result_regex, proc.stdout)
        if not match:
            raise TrialFailed(f"result_regex did not match stdout for command: {command}")
        return float(match.group(1))
    finally:
        if tmp_dir is not None:
            shutil.rmtree(tmp_dir, ignore_errors=True)
