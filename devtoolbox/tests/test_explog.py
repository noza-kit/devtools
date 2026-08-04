from typer.testing import CliRunner

from devtoolbox.explog import log_run
from devtoolbox.explog.cli import app

runner = CliRunner()


def test_log_run_returns_incrementing_ids(devtoolbox_home):
    first_id = log_run(params={"lr": 0.01}, results={"acc": 0.9})
    second_id = log_run(params={"lr": 0.02}, results={"acc": 0.95})

    assert first_id == 1
    assert second_id == 2


def test_log_run_persists_params_results_and_tags(devtoolbox_home):
    log_run(
        params={"lr": 0.01, "epochs": 10},
        results={"accuracy": 0.95, "loss": 0.12},
        tags=["cnn", "baseline"],
    )

    result = runner.invoke(app, ["show", "1"])
    assert result.exit_code == 0, result.output
    assert "Tags: cnn, baseline" in result.output
    assert '"lr": 0.01' in result.output
    assert '"accuracy": 0.95' in result.output


def test_log_run_without_tags_defaults_to_empty(devtoolbox_home):
    log_run(params={"lr": 0.01}, results={"acc": 0.9})

    result = runner.invoke(app, ["show", "1"])
    assert result.exit_code == 0, result.output
    assert "Tags: (none)" in result.output


def test_log_run_handles_non_json_serializable_values(devtoolbox_home):
    class Custom:
        def __str__(self):
            return "custom-value"

    log_run(params={"obj": Custom()}, results={"acc": 0.9})

    result = runner.invoke(app, ["show", "1"])
    assert result.exit_code == 0, result.output
    assert "custom-value" in result.output


def test_cli_list_shows_runs_most_recent_first(devtoolbox_home):
    log_run(params={"lr": 0.01}, results={"acc": 0.9}, tags=["a"])
    log_run(params={"lr": 0.02}, results={"acc": 0.95}, tags=["b"])

    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0, result.output
    lines = [line for line in result.output.splitlines() if line and line[0].isdigit()]
    assert lines[0].startswith("2")
    assert lines[1].startswith("1")


def test_cli_list_respects_limit(devtoolbox_home):
    for i in range(5):
        log_run(params={"i": i}, results={"ok": True})

    result = runner.invoke(app, ["list", "--limit", "2"])
    assert result.exit_code == 0, result.output
    lines = [line for line in result.output.splitlines() if line and line[0].isdigit()]
    assert len(lines) == 2


def test_cli_list_filters_by_tag(devtoolbox_home):
    log_run(params={}, results={}, tags=["work", "urgent"])
    log_run(params={}, results={}, tags=["work"])

    result = runner.invoke(app, ["list", "--tag", "work", "--tag", "urgent"])
    assert result.exit_code == 0, result.output
    lines = [line for line in result.output.splitlines() if line and line[0].isdigit()]
    assert len(lines) == 1
    assert lines[0].startswith("1")


def test_cli_list_empty(devtoolbox_home):
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0, result.output
    assert "No runs found." in result.output


def test_cli_show_nonexistent_fails(devtoolbox_home):
    result = runner.invoke(app, ["show", "999"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_cli_export_csv_to_stdout(devtoolbox_home):
    log_run(params={"lr": 0.01}, results={"acc": 0.9}, tags=["a"])

    result = runner.invoke(app, ["export", "--format", "csv"])
    assert result.exit_code == 0, result.output
    assert "id,timestamp,tags,params,results" in result.output
    assert "a" in result.output


def test_cli_export_csv_to_file(devtoolbox_home, tmp_path):
    log_run(params={"lr": 0.01}, results={"acc": 0.9}, tags=["a"])
    log_run(params={"lr": 0.02}, results={"acc": 0.95}, tags=["b"])

    output_file = tmp_path / "runs.csv"
    result = runner.invoke(app, ["export", "--format", "csv", "--output", str(output_file)])
    assert result.exit_code == 0, result.output
    assert "Exported 2 run(s)" in result.output

    text = output_file.read_text(encoding="utf-8")
    rows = text.strip().splitlines()
    assert rows[0] == "id,timestamp,tags,params,results"
    assert len(rows) == 3


def test_cli_export_filters_by_tag(devtoolbox_home, tmp_path):
    log_run(params={}, results={}, tags=["keep"])
    log_run(params={}, results={}, tags=["drop"])

    output_file = tmp_path / "runs.csv"
    result = runner.invoke(
        app, ["export", "--format", "csv", "--output", str(output_file), "--tag", "keep"]
    )
    assert result.exit_code == 0, result.output

    text = output_file.read_text(encoding="utf-8")
    assert "keep" in text
    assert "drop" not in text


def test_cli_export_unsupported_format_fails(devtoolbox_home):
    result = runner.invoke(app, ["export", "--format", "json"])
    assert result.exit_code == 1
    assert "Unsupported format" in result.output
