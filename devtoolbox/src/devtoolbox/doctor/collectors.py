from __future__ import annotations

import os
import platform
import socket
import subprocess
import sys
from typing import Any


def _run(cmd: list[str], timeout: float = 10.0) -> str | None:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def collect_system() -> dict[str, Any]:
    return {
        "os": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "hostname": socket.gethostname(),
    }


def collect_python() -> dict[str, Any]:
    return {
        "version": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "executable": sys.executable,
        "virtual_env": os.environ.get("VIRTUAL_ENV") or os.environ.get("CONDA_DEFAULT_ENV"),
    }


def collect_hardware() -> dict[str, Any]:
    info: dict[str, Any] = {"logical_cores": os.cpu_count()}
    try:
        import psutil

        info["physical_cores"] = psutil.cpu_count(logical=False)
        vm = psutil.virtual_memory()
        info["memory_total_gb"] = round(vm.total / (1024**3), 2)
        info["memory_available_gb"] = round(vm.available / (1024**3), 2)
    except ImportError:
        info["note"] = "install `psutil` for memory details"
    return info


def collect_gpu() -> list[str]:
    nvidia = _run(
        ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"]
    )
    if nvidia:
        return [line.strip() for line in nvidia.splitlines() if line.strip()]

    system = platform.system()
    if system == "Windows":
        out = _run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name",
            ]
        )
        if out:
            return [line.strip() for line in out.splitlines() if line.strip()]
    elif system == "Linux":
        out = _run(["lspci"])
        if out:
            return [
                line.strip()
                for line in out.splitlines()
                if "VGA" in line or "3D controller" in line
            ]
    elif system == "Darwin":
        out = _run(["system_profiler", "SPDisplaysDataType"])
        if out:
            return [
                line.split(":", 1)[1].strip()
                for line in out.splitlines()
                if "Chipset Model" in line
            ]

    return []


def collect_git() -> dict[str, Any] | None:
    if _run(["git", "rev-parse", "--is-inside-work-tree"]) != "true":
        return None
    status = _run(["git", "status", "--porcelain"])
    return {
        "remote": _run(["git", "config", "--get", "remote.origin.url"]),
        "branch": _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
        "commit": _run(["git", "rev-parse", "HEAD"]),
        "dirty": bool(status),
    }


def collect_pip_freeze() -> list[str]:
    out = _run([sys.executable, "-m", "pip", "freeze"], timeout=30.0)
    return out.splitlines() if out else []


def collect_report(include_pip: bool = False, include_gpu: bool = True) -> dict[str, Any]:
    report: dict[str, Any] = {
        "system": collect_system(),
        "python": collect_python(),
        "hardware": collect_hardware(),
    }
    if include_gpu:
        report["gpu"] = collect_gpu()

    git_info = collect_git()
    if git_info is not None:
        report["git"] = git_info

    if include_pip:
        report["pip_freeze"] = collect_pip_freeze()

    return report


def format_human(report: dict[str, Any]) -> str:
    lines: list[str] = []

    def section(title: str, data: Any) -> None:
        lines.append(f"== {title} ==")
        if isinstance(data, dict):
            has_content = False
            for key, value in data.items():
                if value in (None, "", []):
                    continue
                lines.append(f"  {key}: {value}")
                has_content = True
            if not has_content:
                lines.append("  (none)")
        elif isinstance(data, list):
            if not data:
                lines.append("  (none detected)")
            for item in data:
                lines.append(f"  - {item}")
        lines.append("")

    section("System", report.get("system", {}))
    section("Python", report.get("python", {}))
    section("Hardware", report.get("hardware", {}))
    if "gpu" in report:
        section("GPU", report["gpu"])
    if "git" in report:
        section("Git", report["git"])
    if "pip_freeze" in report:
        section("Installed packages (pip freeze)", report["pip_freeze"])

    return "\n".join(lines).rstrip() + "\n"
