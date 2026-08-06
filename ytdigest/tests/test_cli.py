from __future__ import annotations

from typer.testing import CliRunner

from ytdigest import batch
from ytdigest.cli import app

runner = CliRunner()

REQUIRED_ENV = {
    "DISCORD_WEBHOOK_NEW": "https://discord.com/api/webhooks/1/new",
    "DISCORD_WEBHOOK_ARCHIVE": "https://discord.com/api/webhooks/2/archive",
    "DISCORD_BOT_TOKEN": "bot-token",
    "DISCORD_NEW_CHANNEL_ID": "555555",
    "TWITCH_CLIENT_ID": "twitch-id",
    "TWITCH_CLIENT_SECRET": "twitch-secret",
}


def _write_channels(tmp_path):
    path = tmp_path / "channels.yaml"
    path.write_text(
        "youtube:\n  - channel_id: UCxxxx\n    name: Example\ntwitch:\n  - login: streamer1\n    name: Streamer1\n",
        encoding="utf-8",
    )
    return path


def test_run_invokes_batch_with_loaded_config(tmp_path, monkeypatch):
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    channels_path = _write_channels(tmp_path)
    db_path = tmp_path / "data" / "state.db"

    calls = []
    monkeypatch.setattr(batch, "run", lambda db, channels, secrets: calls.append((channels, secrets)))

    result = runner.invoke(app, ["--channels", str(channels_path), "--db", str(db_path)])

    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    channels_obj, secrets_obj = calls[0]
    assert channels_obj.youtube[0].channel_id == "UCxxxx"
    assert secrets_obj.twitch_client_id == "twitch-id"
    assert db_path.exists()


def test_run_missing_secret_exits_nonzero(tmp_path, monkeypatch):
    for key, value in REQUIRED_ENV.items():
        if key != "TWITCH_CLIENT_SECRET":
            monkeypatch.setenv(key, value)
    monkeypatch.delenv("TWITCH_CLIENT_SECRET", raising=False)
    channels_path = _write_channels(tmp_path)

    result = runner.invoke(app, ["--channels", str(channels_path), "--db", str(tmp_path / "state.db")])

    assert result.exit_code == 1
    assert "TWITCH_CLIENT_SECRET" in result.output


def test_run_missing_channels_file_exits_nonzero(tmp_path, monkeypatch):
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)

    result = runner.invoke(
        app, ["--channels", str(tmp_path / "missing.yaml"), "--db", str(tmp_path / "state.db")]
    )

    assert result.exit_code == 1
