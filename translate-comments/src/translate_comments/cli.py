from __future__ import annotations

import sys
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from confload import ConfigError, load_config

for _stream in (sys.stdout, sys.stderr):
    # On Windows, stdout/stderr often default to the system codepage (e.g. cp932)
    # rather than UTF-8, which mangles non-ASCII comment text (Japanese, etc.)
    # when printed to a UTF-8 terminal.
    if hasattr(_stream, "reconfigure") and (_stream.encoding or "").lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8")

from translate_comments.deepl_client import (
    SUPPORTED_LANGUAGES,
    DeepLClient,
    DeepLConfigError,
    DeepLError,
    load_api_key,
)
from translate_comments.extractor import CommentBlock, extract_comments
from translate_comments.languages import EXTENSION_PROFILES, UnsupportedFileTypeError, get_profile
from translate_comments.writer import render_inline, render_separate, separate_output_path

app = typer.Typer(
    help="Translate source code comments (ja/en/fr) via DeepL, leaving the code itself untouched",
    add_completion=True,
)


class Mode(str, Enum):
    inline = "inline"
    separate = "separate"
    replace = "replace"


@app.command()
def main(
    path: Path = typer.Argument(..., help="Translate this file, or every matching file under this directory"),
    from_lang: str = typer.Option(..., "--from", help="Source language code: ja, en, or fr"),
    to_langs: str = typer.Option(..., "--to", help="Target language code(s), comma-separated, e.g. en,fr"),
    mode: Mode = typer.Option(
        Mode.inline, "--mode",
        help="inline: append translations directly below each comment. "
        "separate: write one translated copy per target language (e.g. file_en.py), original untouched. "
        "replace: overwrite the original file's comments in place with the translation (single --to language only)",
    ),
    recursive: bool = typer.Option(False, "--recursive/--no-recursive", help="Recurse into subdirectories"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview the comments that would be translated; call DeepL and write nothing"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt"),
    config: Optional[Path] = typer.Option(
        None, "--config", help="confload YAML/JSON config file to read deepl_api_key from"
    ),
) -> None:
    """Preview, then translate comments in PATH (a file or a directory)."""
    if not path.exists():
        typer.secho(f"Not found: {path}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if path.is_file():
        try:
            get_profile(path)
        except UnsupportedFileTypeError as exc:
            typer.secho(str(exc), fg=typer.colors.RED)
            raise typer.Exit(code=1)

    from_lang = from_lang.strip().lower()
    to_list = _parse_target_langs(from_lang, to_langs)

    if mode is Mode.replace and len(to_list) != 1:
        typer.secho(
            "--mode replace overwrites the original file in place, so it only supports a single "
            f"--to language (got: {','.join(to_list)})",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    files = _find_files(path, recursive=recursive)
    plan = _build_plan(files)
    if not plan:
        typer.echo("No translatable comments found.")
        return

    _print_preview(plan, path)

    if dry_run:
        typer.echo("(dry run, no API calls made and no files written)")
        return

    if mode is Mode.replace:
        typer.secho(
            "--mode replace will overwrite the original comments in these file(s); "
            "the original-language text will be lost unless it's saved elsewhere (e.g. version control).",
            fg=typer.colors.YELLOW,
        )

    if not yes and not typer.confirm("Translate now?"):
        typer.echo("Aborted.")
        raise typer.Exit(code=1)

    try:
        config_obj = load_config(config) if config is not None else None
        api_key = load_api_key(config_obj)
    except (ConfigError, DeepLConfigError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)

    try:
        _translate_and_write(plan, api_key=api_key, from_lang=from_lang, to_list=to_list, mode=mode)
    except DeepLError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho(
        f"Translated {sum(len(blocks) for _, _, blocks in plan)} comment(s) across {len(plan)} file(s).",
        fg=typer.colors.GREEN,
    )


_FilePlan = tuple[Path, str, list[CommentBlock]]


def _parse_target_langs(from_lang: str, to_langs: str) -> list[str]:
    if from_lang not in SUPPORTED_LANGUAGES:
        typer.secho(
            f"Unsupported --from language {from_lang!r} (supported: {sorted(SUPPORTED_LANGUAGES)})",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    to_list = [t.strip().lower() for t in to_langs.split(",") if t.strip()]
    invalid = [t for t in to_list if t not in SUPPORTED_LANGUAGES]
    if invalid:
        typer.secho(
            f"Unsupported --to language(s) {invalid} (supported: {sorted(SUPPORTED_LANGUAGES)})",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    to_list = [t for t in to_list if t != from_lang]
    if not to_list:
        typer.secho("--to must include at least one language different from --from", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    return to_list


def _find_files(path: Path, *, recursive: bool) -> list[Path]:
    if path.is_file():
        return [path]

    patterns = [f"*{ext}" for ext in EXTENSION_PROFILES]
    glob = path.rglob if recursive else path.glob
    return sorted({f for pattern in patterns for f in glob(pattern) if f.is_file()})


def _build_plan(files: list[Path]) -> list[_FilePlan]:
    plan: list[_FilePlan] = []
    for f in files:
        blocks = extract_comments(f)
        if blocks:
            text = f.read_text(encoding="utf-8")
            plan.append((f, text, blocks))
    return plan


def _print_preview(plan: list[_FilePlan], root: Path) -> None:
    for f, _text, blocks in plan:
        rel = f.relative_to(root) if root.is_dir() else f
        typer.echo(f"{rel}")
        for b in blocks:
            snippet = b.text.splitlines()[0][:60]
            typer.echo(f"  [{b.start_line}-{b.end_line}] {b.style}: {snippet}")

    total_blocks = sum(len(blocks) for _, _, blocks in plan)
    typer.echo(f"{total_blocks} comment(s) across {len(plan)} file(s) will be translated.")


def _translate_and_write(
    plan: list[_FilePlan], *, api_key: str, from_lang: str, to_list: list[str], mode: Mode
) -> None:
    all_texts = [b.text for _, _, blocks in plan for b in blocks]

    with DeepLClient(api_key=api_key) as client:
        all_translations = client.translate_to_many(all_texts, source_lang=from_lang, target_langs=to_list)

    offset = 0
    for f, text, blocks in plan:
        n = len(blocks)
        per_file = {lang: all_translations[lang][offset : offset + n] for lang in to_list}
        offset += n

        if mode is Mode.inline:
            f.write_text(render_inline(text, blocks, per_file, to_list), encoding="utf-8")
        elif mode is Mode.replace:
            f.write_text(render_separate(text, blocks, per_file[to_list[0]]), encoding="utf-8")
        else:
            for lang in to_list:
                out_path = separate_output_path(f, lang)
                out_path.write_text(render_separate(text, blocks, per_file[lang]), encoding="utf-8")


if __name__ == "__main__":
    app()
