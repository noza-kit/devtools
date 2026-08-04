import pytest


@pytest.fixture
def devtoolbox_home(monkeypatch, tmp_path):
    home = tmp_path / "devtools_home"
    monkeypatch.setenv("DEVTOOLBOX_HOME", str(home))
    return home
