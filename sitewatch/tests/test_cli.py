from __future__ import annotations

from typer.testing import CliRunner

from sitewatch.cli import app

runner = CliRunner()

URL = "https://example.test/page"


def test_add_watch(sitewatch_home):
    result = runner.invoke(app, ["add", URL, "--selector", "#price", "--name", "Example Site"])

    assert result.exit_code == 0, result.output
    assert "Added watch #1" in result.output


def test_add_with_custom_min_interval(sitewatch_home):
    result = runner.invoke(
        app, ["add", URL, "--selector", "#price", "--name", "Example Site", "--min-interval", "60"]
    )

    assert result.exit_code == 0, result.output

    list_result = runner.invoke(app, ["list"])
    assert "60s" in list_result.output


def test_add_duplicate_fails(sitewatch_home):
    runner.invoke(app, ["add", URL, "--selector", "#price", "--name", "Example Site"])
    result = runner.invoke(app, ["add", URL, "--selector", "#price", "--name", "Example Site Again"])

    assert result.exit_code == 1
    assert "already watching" in result.output


def test_list_empty(sitewatch_home):
    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "No watches registered" in result.output


def test_list_shows_registered_watches(sitewatch_home):
    runner.invoke(app, ["add", URL, "--selector", "#price", "--name", "Example Site"])

    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "Example Site" in result.output
    assert "(never)" in result.output


def test_remove_watch(sitewatch_home):
    runner.invoke(app, ["add", URL, "--selector", "#price", "--name", "Example Site"])

    result = runner.invoke(app, ["remove", "1"])
    assert result.exit_code == 0
    assert "Removed watch #1" in result.output

    list_result = runner.invoke(app, ["list"])
    assert "No watches registered" in list_result.output


def test_remove_missing_watch_fails(sitewatch_home):
    result = runner.invoke(app, ["remove", "999"])

    assert result.exit_code == 1
    assert "no watch" in result.output


def test_start_with_no_watches_fails_fast(sitewatch_home):
    result = runner.invoke(app, ["start"])

    assert result.exit_code == 1
    assert "No watches registered" in result.output
