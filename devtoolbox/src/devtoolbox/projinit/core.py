from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Template

from devtoolbox.projinit.config import LanguageConfig, README_TEMPLATE


@dataclass
class InitResult:
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    git_initialized: bool = False


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


def generate_gitignore(target_dir: Path, language: LanguageConfig, result: InitResult) -> None:
    content = language.gitignore_path.read_text(encoding="utf-8")
    _write_if_absent(target_dir / ".gitignore", content, result)


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
) -> InitResult:
    target_dir.mkdir(parents=True, exist_ok=True)
    result = InitResult()

    if do_git_init:
        result.git_initialized = run_git_init(target_dir)

    generate_gitignore(target_dir, language, result)
    generate_readme(target_dir, project_name, description, language, result)
    generate_extra_files(target_dir, project_name, description, language, result)

    return result
