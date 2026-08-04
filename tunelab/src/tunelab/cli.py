from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from tunelab import report
from tunelab.backends import BackendError, get_backend
from tunelab.config import Config, ConfigError
from tunelab.paths import list_study_names
from tunelab.study import StudyNotFoundError, delete_study, load_study, open_study
from tunelab.templates import render_template

app = typer.Typer(help="Hyperparameter tuning experiment manager built on Optuna", add_completion=True)


def _load_config(config_path: Path) -> Config:
    try:
        return Config.load(config_path)
    except ConfigError as exc:
        typer.secho(f"Config error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


def _load_study(study_name: str):
    try:
        return load_study(study_name)
    except StudyNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command()
def init(
    name: str = typer.Argument(..., help="Study name"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output YAML path (default: <name>.yaml)"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite an existing file"),
) -> None:
    """Create a starter config YAML for a new study."""
    path = output or Path(f"{name}.yaml")
    if path.exists() and not force:
        typer.secho(f"{path} already exists (use --force to overwrite)", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)
    path.write_text(render_template(name), encoding="utf-8")
    typer.secho(f"Wrote {path}", fg=typer.colors.GREEN)


@app.command()
def run(
    config_path: Path = typer.Argument(..., help="Path to a study config YAML"),
    n_trials: Optional[int] = typer.Option(None, "--n-trials", help="Override budget.n_trials"),
    timeout: Optional[float] = typer.Option(None, "--timeout", help="Override budget.timeout (seconds)"),
    n_jobs: Optional[int] = typer.Option(None, "--n-jobs", help="Override budget.n_jobs"),
    fresh: bool = typer.Option(False, "--fresh", help="Discard any existing study with this name and start over"),
) -> None:
    """Run the optimization loop for a study, resuming it if it already exists."""
    config = _load_config(config_path)
    if n_trials is not None:
        config.budget.n_trials = n_trials
    if timeout is not None:
        config.budget.timeout = timeout
    if n_jobs is not None:
        config.budget.n_jobs = n_jobs

    try:
        backend_fn = get_backend(config.backend)
    except BackendError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)

    study = open_study(config, fresh=fresh)
    typer.echo(f"Running study {config.study!r} with backend={config.backend!r} ...")

    try:
        backend_fn(study, config)
    except ConfigError as exc:
        typer.secho(f"Config error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except BackendError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)

    summary = report.summarize(study)
    typer.secho(f"Finished. {summary['n_trials']} trial(s): {summary['states']}", fg=typer.colors.GREEN)
    if summary["best"]:
        typer.echo(f"Best value={summary['best']['value']} params={summary['best']['params']}")


@app.command()
def status(study_name: str = typer.Argument(..., help="Study name")) -> None:
    """Show trial counts and the current best result for a study."""
    study = _load_study(study_name)
    summary = report.summarize(study)
    typer.echo(f"study: {summary['study_name']} (direction={summary['direction']})")
    typer.echo(f"trials: {summary['n_trials']} {summary['states']}")
    if summary["best"]:
        typer.echo(f"best: value={summary['best']['value']} params={summary['best']['params']}")
    else:
        typer.echo("best: (no completed trials yet)")


@app.command()
def best(
    study_name: str = typer.Argument(..., help="Study name"),
    top: int = typer.Option(5, "--top", "-n", help="Number of top trials to show"),
) -> None:
    """Show the top-N trials by value."""
    study = _load_study(study_name)
    trials = report.top_trials(study, n=top)
    if not trials:
        typer.echo("No completed trials yet.")
        return
    for t in trials:
        typer.echo(f"#{t.number} value={t.value} params={t.params}")


@app.command(name="list")
def list_cmd(
    study_name: str = typer.Argument(..., help="Study name"),
    state: Optional[str] = typer.Option(None, "--state", help="Filter by state: complete|fail|running|pruned"),
    sort: str = typer.Option("number", "--sort", help="Sort by: number|value|duration"),
) -> None:
    """List all trials for a study."""
    study = _load_study(study_name)
    try:
        trials = report.list_trials(study, state=state, sort=sort)
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)
    if not trials:
        typer.echo("No trials found.")
        return
    for t in trials:
        typer.echo(f"#{t.number} [{t.state.name}] value={t.value} params={t.params}")


@app.command()
def export(
    study_name: str = typer.Argument(..., help="Study name"),
    output: Path = typer.Option(Path("results.csv"), "--output", "-o", help="Output CSV path"),
) -> None:
    """Export all trials to a CSV file."""
    study = _load_study(study_name)
    n = report.export_csv(study, output)
    typer.secho(f"Exported {n} trial(s) to {output}", fg=typer.colors.GREEN)


@app.command()
def plot(
    study_name: str = typer.Argument(..., help="Study name"),
    output: Path = typer.Option(Path("report.html"), "--output", "-o", help="Output HTML path"),
) -> None:
    """Render optimization history / param importance / parallel coordinate plots to HTML."""
    study = _load_study(study_name)
    try:
        report.plot_report(study, output)
    except RuntimeError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)
    typer.secho(f"Wrote {output}", fg=typer.colors.GREEN)


@app.command()
def dashboard(study_name: str = typer.Argument(..., help="Study name")) -> None:
    """Launch optuna-dashboard for a study (requires the 'dashboard' extra)."""
    from tunelab.paths import storage_url

    try:
        from optuna_dashboard import run_server
    except ImportError:
        typer.secho(
            "optuna-dashboard is not installed. Install with: pip install tunelab[dashboard]",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    _load_study(study_name)
    run_server(storage_url(study_name))


@app.command(name="studies")
def studies_cmd() -> None:
    """List known study names."""
    names = list_study_names()
    if not names:
        typer.echo("No studies found. Run 'tune run <config.yaml>' to create one.")
        return
    for name in names:
        typer.echo(name)


@app.command()
def delete(
    study_name: str = typer.Argument(..., help="Study name"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt"),
) -> None:
    """Delete a study and all its trial data."""
    if not yes:
        typer.confirm(f"Delete study {study_name!r} and all its trials?", abort=True)
    try:
        delete_study(study_name)
    except StudyNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)
    typer.secho(f"Deleted {study_name!r}", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
