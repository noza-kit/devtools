import pytest


@pytest.fixture
def devtoolbox_home(monkeypatch, tmp_path):
    home = tmp_path / "devtools_home"
    monkeypatch.setenv("DEVTOOLBOX_HOME", str(home))
    return home


@pytest.fixture
def fake_home(monkeypatch, tmp_path):
    """A fake $HOME for dotsync tests, so real symlinks never touch the real home dir."""
    home = tmp_path / "fake_home"
    home.mkdir()
    monkeypatch.setenv("DOTSYNC_HOME", str(home))
    return home
