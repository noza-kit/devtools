from typer.testing import CliRunner

from devtoolbox.dotsync.cli import app

runner = CliRunner()


def _make_source(tmp_path):
    source = tmp_path / "dotfiles_src"
    source.mkdir()
    (source / ".bashrc").write_text("export A=1\n", encoding="utf-8")
    config_dir = source / ".config"
    config_dir.mkdir()
    (config_dir / "settings.yaml").write_text("key: value\n", encoding="utf-8")
    (source / "README.md").write_text("not a dotfile\n", encoding="utf-8")
    return source


def test_link_creates_symlinks_and_ignores_non_dotfiles(fake_home, tmp_path):
    source = _make_source(tmp_path)

    result = runner.invoke(app, ["link", "--source", str(source)])
    assert result.exit_code == 0, result.output

    bashrc = fake_home / ".bashrc"
    assert bashrc.is_symlink()
    assert bashrc.resolve() == (source / ".bashrc").resolve()
    assert (fake_home / ".config").is_symlink()
    assert not (fake_home / "README.md").exists()


def test_link_is_idempotent(fake_home, tmp_path):
    source = _make_source(tmp_path)
    runner.invoke(app, ["link", "--source", str(source)])

    result = runner.invoke(app, ["link", "--source", str(source)])
    assert result.exit_code == 0, result.output
    assert "already linked" in result.output


def test_link_conflict_without_force_leaves_file_untouched(fake_home, tmp_path):
    source = _make_source(tmp_path)
    (fake_home / ".bashrc").write_text("original content\n", encoding="utf-8")

    result = runner.invoke(app, ["link", "--source", str(source)])
    assert result.exit_code == 0, result.output
    assert "conflict" in result.output
    assert (fake_home / ".bashrc").read_text(encoding="utf-8") == "original content\n"
    assert not (fake_home / ".bashrc").is_symlink()


def test_link_force_backs_up_and_replaces(fake_home, tmp_path):
    source = _make_source(tmp_path)
    (fake_home / ".bashrc").write_text("original content\n", encoding="utf-8")

    result = runner.invoke(app, ["link", "--source", str(source), "--force"])
    assert result.exit_code == 0, result.output

    assert (fake_home / ".bashrc").is_symlink()
    backup = fake_home / ".bashrc.bak"
    assert backup.read_text(encoding="utf-8") == "original content\n"


def test_status_reports_linked_and_missing(fake_home, tmp_path):
    source = _make_source(tmp_path)
    runner.invoke(app, ["link", "--source", str(source)])
    (fake_home / ".bashrc").unlink()

    result = runner.invoke(app, ["status", "--source", str(source)])
    assert result.exit_code == 0, result.output
    assert ".bashrc: missing" in result.output
    assert ".config: linked" in result.output


def test_unlink_removes_symlink_and_restores_backup(fake_home, tmp_path):
    source = _make_source(tmp_path)
    (fake_home / ".bashrc").write_text("original content\n", encoding="utf-8")
    runner.invoke(app, ["link", "--source", str(source), "--force"])

    result = runner.invoke(app, ["unlink", "--source", str(source)])
    assert result.exit_code == 0, result.output

    bashrc = fake_home / ".bashrc"
    assert not bashrc.is_symlink()
    assert bashrc.read_text(encoding="utf-8") == "original content\n"
    assert not (fake_home / ".bashrc.bak").exists()


def test_source_not_found_fails(fake_home, tmp_path):
    missing = tmp_path / "does_not_exist"
    result = runner.invoke(app, ["link", "--source", str(missing)])
    assert result.exit_code == 1
    assert "not found" in result.output
