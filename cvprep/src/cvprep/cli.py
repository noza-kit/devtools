from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
import yaml

from cvprep.clipboard import ClipboardUnavailableError, write_clipboard
from cvprep.codegen import generate_script
from cvprep.io import ImageReadError, load_image, save_image
from cvprep.pipeline import Pipeline, UnknownOpError
from cvprep.presets import (
    PresetNotFoundError,
    get_preset,
    init_presets_file,
    list_preset_names,
    presets_path,
)

app = typer.Typer(help="OpenCV preprocessing one-liners driven by YAML presets", add_completion=True)

DEFAULT_IMAGE_GLOBS = ["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.tif", "*.tiff"]


def _run_pipeline(preset: str, input_path: Path):
    image = load_image(input_path)
    pipeline = Pipeline.from_preset(preset)
    return pipeline.run(image)


@app.command()
def run(
    preset: str = typer.Argument(..., help="Preset name from presets.yaml"),
    input: Path = typer.Argument(..., help="Input image path"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output path (default: <input stem>.cvprep<suffix>)"
    ),
    show: bool = typer.Option(False, "--show", help="Display the result in a window"),
) -> None:
    """Apply a preset to a single image."""
    try:
        result = _run_pipeline(preset, input)
    except (PresetNotFoundError, UnknownOpError, ImageReadError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)

    out_path = output or input.with_name(f"{input.stem}.cvprep{input.suffix}")
    save_image(out_path, result)
    typer.secho(f"Wrote {out_path}", fg=typer.colors.GREEN)

    if show:
        import cv2

        cv2.imshow(preset, result)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


@app.command()
def batch(
    preset: str = typer.Argument(..., help="Preset name from presets.yaml"),
    input_dir: Path = typer.Argument(..., help="Directory of input images"),
    output_dir: Optional[Path] = typer.Option(
        None, "--output-dir", "-d", help="Output directory (default: <input_dir>/cvprep_out)"
    ),
    pattern: Optional[str] = typer.Option(
        None, "--pattern", "-p", help="Glob pattern (repeatable via comma-separated list; default: common image extensions)"
    ),
) -> None:
    """Apply a preset to every matching image in a directory."""
    if not input_dir.is_dir():
        typer.secho(f"Not a directory: {input_dir}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    patterns = [p.strip() for p in pattern.split(",")] if pattern else DEFAULT_IMAGE_GLOBS
    files = sorted({f for pat in patterns for f in input_dir.glob(pat)})
    if not files:
        typer.echo("No matching images found.")
        return

    out_dir = output_dir or (input_dir / "cvprep_out")

    try:
        pipeline = Pipeline.from_preset(preset)
    except PresetNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)

    processed = 0
    for f in files:
        try:
            image = load_image(f)
            result = pipeline.run(image)
        except (UnknownOpError, ImageReadError) as exc:
            typer.secho(f"{f}: {exc}", fg=typer.colors.RED)
            continue
        save_image(out_dir / f.name, result)
        processed += 1

    typer.secho(f"Processed {processed}/{len(files)} image(s) into {out_dir}", fg=typer.colors.GREEN)


@app.command(name="list")
def list_cmd() -> None:
    """List preset names defined in presets.yaml."""
    names = list_preset_names()
    if not names:
        typer.echo(f"No presets found. Run 'cvprep init' to create {presets_path()}.")
        return
    for name in names:
        typer.echo(name)


@app.command()
def show(preset: str = typer.Argument(..., help="Preset name")) -> None:
    """Print a preset's pipeline steps."""
    try:
        steps = get_preset(preset)
    except PresetNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.echo(yaml.safe_dump(steps, sort_keys=False))


@app.command()
def export(
    preset: str = typer.Argument(..., help="Preset name"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Write the generated script to this file"
    ),
    copy: bool = typer.Option(False, "--copy", "-c", help="Copy the generated script to the clipboard"),
    input_path: str = typer.Option(
        "input.jpg", "--input-path", help="Path baked into the generated script's cv2.imread() call"
    ),
    output_path: str = typer.Option(
        "output.jpg", "--output-path", help="Path baked into the generated script's cv2.imwrite() call"
    ),
) -> None:
    """Render a preset's pipeline as a standalone Python script.

    With neither --output nor --copy, the script is printed to stdout.
    """
    try:
        steps = get_preset(preset)
        script = generate_script(steps, input_path=input_path, output_path=output_path)
    except (PresetNotFoundError, UnknownOpError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if not output and not copy:
        typer.echo(script)
        return

    if output:
        output.write_text(script, encoding="utf-8")
        typer.secho(f"Wrote {output}", fg=typer.colors.GREEN)

    if copy:
        try:
            write_clipboard(script)
        except ClipboardUnavailableError as exc:
            typer.secho(f"Clipboard unavailable: {exc}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        typer.secho("Copied to clipboard", fg=typer.colors.GREEN)


@app.command()
def init(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite an existing presets.yaml"),
) -> None:
    """Create a starter presets.yaml with example presets."""
    path = presets_path()
    if init_presets_file(force=force):
        typer.secho(f"Wrote {path}", fg=typer.colors.GREEN)
    else:
        typer.secho(f"{path} already exists (use --force to overwrite)", fg=typer.colors.YELLOW)


if __name__ == "__main__":
    app()
