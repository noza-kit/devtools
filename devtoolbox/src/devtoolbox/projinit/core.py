from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Template

from devtoolbox.projinit.config import LanguageConfig, README_TEMPLATE, get_license_template


@dataclass
class InitResult:
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    git_initialized: bool = False
    command_run: str | None = None
    command_error: str | None = None


def _write_if_absent(path: Path, content: str, result: InitResult) -> None:
    if path.exists():
        result.skipped.append(str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    result.created.append(str(path))


def run_git_init(target_dir: Path) -> bool:
    if (target_dir / ".git").exists():
        return False
    subprocess.run(
        ["git", "init"],
        cwd=target_dir,
        check=True,
        capture_output=True,
    )
    return True


def run_language_init_command(
    target_dir: Path, language: LanguageConfig, result: InitResult
) -> None:
    if not language.init_command:
        return
    command_str = " ".join(language.init_command)
    try:
        subprocess.run(
            language.init_command,
            cwd=target_dir,
            check=True,
            capture_output=True,
        )
        result.command_run = command_str
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        result.command_error = f"{command_str}: {exc}"


def generate_gitignore(target_dir: Path, language: LanguageConfig, result: InitResult) -> None:
    content = language.gitignore_path.read_text(encoding="utf-8")
    _write_if_absent(target_dir / ".gitignore", content, result)


def generate_license(target_dir: Path, license_key: str, author: str, result: InitResult) -> None:
    template_path = get_license_template(license_key)
    template = Template(template_path.read_text(encoding="utf-8"))
    content = template.render(year=datetime.now(timezone.utc).year, author=author)
    _write_if_absent(target_dir / "LICENSE", content, result)


def generate_readme(
    target_dir: Path,
    project_name: str,
    description: str,
    language: LanguageConfig,
    result: InitResult,
) -> None:
    template = Template(README_TEMPLATE.read_text(encoding="utf-8"))
    content = template.render(
        project_name=project_name,
        description=description,
        language_display_name=language.display_name,
    )
    _write_if_absent(target_dir / "README.md", content, result)


def generate_extra_files(
    target_dir: Path,
    project_name: str,
    description: str,
    language: LanguageConfig,
    result: InitResult,
) -> None:
    for extra in language.extra_files:
        template = Template(extra.content)
        content = template.render(project_name=project_name, description=description)
        _write_if_absent(target_dir / extra.path, content, result)


def init_project(
    target_dir: Path,
    project_name: str,
    description: str,
    language: LanguageConfig,
    do_git_init: bool = True,
    do_init_command: bool = True,
    license_key: str | None = None,
    author: str = "Unknown",
) -> InitResult:
    target_dir.mkdir(parents=True, exist_ok=True)
    result = InitResult()

    if do_git_init:
        result.git_initialized = run_git_init(target_dir)

    if do_init_command:
        run_language_init_command(target_dir, language, result)

    generate_gitignore(target_dir, language, result)
    if license_key:
        generate_license(target_dir, license_key, author, result)
    generate_readme(target_dir, project_name, description, language, result)
    generate_extra_files(target_dir, project_name, description, language, result)

    return result
