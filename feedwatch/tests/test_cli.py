from __future__ import annotations

from typer.testing import CliRunner

from feedwatch.cli import app

runner = CliRunner()

FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id=UCabcdefghijklmnopqrstuv"


def test_add_rss_watch(feedwatch_home):
    result = runner.invoke(app, ["add", FEED_URL, "--name", "Example Channel", "--tags", "youtube"])

    assert result.exit_code == 0, result.output
    assert "Added watch #1" in result.output


def test_add_expands_bare_youtube_channel_id(feedwatch_home):
    result = runner.invoke(app, ["add", "UCabcdefghijklmnopqrstuv", "--name", "Example Channel"])

    assert result.exit_code == 0, result.output
    assert FEED_URL in result.output


def test_add_duplicate_fails(feedwatch_home):
    runner.invoke(app, ["add", FEED_URL, "--name", "Example Channel"])
    result = runner.invoke(app, ["add", FEED_URL, "--name", "Example Channel Again"])

    assert result.exit_code == 1
    assert "already watching" in result.output


def test_add_twitch_watch(feedwatch_home):
    result = runner.invoke(app, ["add-twitch", "SomeStreamer", "--name", "Some Streamer", "--tags", "twitch"])

    assert result.exit_code == 0, result.output
    assert "Added watch #1" in result.output
    assert "twitch.tv/somestreamer" in result.output


def test_list_empty(feedwatch_home):
    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "No watches registered" in result.output


def test_list_shows_registered_watches(feedwatch_home):
    runner.invoke(app, ["add", FEED_URL, "--name", "Example Channel", "--tags", "youtube"])
    runner.invoke(app, ["add-twitch", "somestreamer", "--name", "Some Streamer"])

    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "Example Channel" in result.output
    assert "Some Streamer" in result.output


def test_remove_watch(feedwatch_home):
    runner.invoke(app, ["add", FEED_URL, "--name", "Example Channel"])

    result = runner.invoke(app, ["remove", "1"])
    assert result.exit_code == 0
    assert "Removed watch #1" in result.output

    list_result = runner.invoke(app, ["list"])
    assert "No watches registered" in list_result.output


def test_remove_missing_watch_fails(feedwatch_home):
    result = runner.invoke(app, ["remove", "999"])

    assert result.exit_code == 1
    assert "no watch" in result.output


def test_start_with_no_watches_fails_fast(feedwatch_home):
    result = runner.invoke(app, ["start"])

    assert result.exit_code == 1
    assert "No watches registered" in result.output
