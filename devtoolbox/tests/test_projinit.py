from typer.testing import CliRunner

from devtoolbox.projinit.cli import app

runner = CliRunner()


def test_init_python_project_creates_expected_files(devtoolbox_home, tmp_path):
    target = tmp_path / "myproject"
    result = runner.invoke(
        app,
        [
            "--name",
            "myproject",
            "--lang",
            "python",
            "--description",
            "a test project",
            "--dir",
            str(target),
            "--no-git",
            "--no-run-init-command",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (target / ".gitignore").exists()
    assert (target / "README.md").exists()
    assert (target / "requirements.txt").exists()
    assert not (target / "LICENSE").exists()

    readme = (target / "README.md").read_text(encoding="utf-8")
    assert "myproject" in readme
    assert "a test project" in readme

    gitignore = (target / ".gitignore").read_text(encoding="utf-8")
    assert "__pycache__" in gitignore


def test_init_runs_git_init(devtoolbox_home, tmp_path):
    target = tmp_path / "gitproject"
    result = runner.invoke(
        app,
        [
            "--name",
            "gitproject",
            "--lang",
            "generic",
            "--description",
            "a git project",
            "--dir",
            str(target),
            "--no-run-init-command",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (target / ".git").exists()


def test_init_unknown_language_fails(devtoolbox_home, tmp_path):
    target = tmp_path / "badproject"
    result = runner.invoke(
        app,
        [
            "--name",
            "badproject",
            "--lang",
            "cobol",
            "--dir",
            str(target),
            "--no-git",
            "--no-run-init-command",
        ],
    )

    assert result.exit_code == 1
    assert "Unknown language" in result.output


def test_init_does_not_overwrite_existing_files(devtoolbox_home, tmp_path):
    target = tmp_path / "existingproject"
    target.mkdir()
    (target / "README.md").write_text("keep me", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "--name",
            "existingproject",
            "--lang",
            "python",
            "--description",
            "already exists",
            "--dir",
            str(target),
            "--no-git",
            "--no-run-init-command",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (target / "README.md").read_text(encoding="utf-8") == "keep me"


def test_init_runs_init_command_creates_venv(devtoolbox_home, tmp_path):
    target = tmp_path / "venvproject"
    result = runner.invoke(
        app,
        [
            "--name",
            "venvproject",
            "--lang",
            "python",
            "--description",
            "venv test",
            "--dir",
            str(target),
            "--no-git",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (target / ".venv").exists()
    assert "ran: python -m venv .venv" in result.output


def test_init_generates_mit_license(devtoolbox_home, tmp_path):
    target = tmp_path / "licensedproject"
    result = runner.invoke(
        app,
        [
            "--name",
            "licensedproject",
            "--lang",
            "generic",
            "--description",
            "licensed",
            "--dir",
            str(target),
            "--no-git",
            "--no-run-init-command",
            "--license",
            "mit",
            "--author",
            "Jane Doe",
        ],
    )

    assert result.exit_code == 0, result.output
    license_text = (target / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in license_text
    assert "Jane Doe" in license_text


def test_init_unknown_license_fails(devtoolbox_home, tmp_path):
    target = tmp_path / "badlicenseproject"
    result = runner.invoke(
        app,
        [
            "--name",
            "badlicenseproject",
            "--lang",
            "generic",
            "--description",
            "bad license",
            "--dir",
            str(target),
            "--no-git",
            "--no-run-init-command",
            "--license",
            "wtfpl",
        ],
    )

    assert result.exit_code == 1
    assert "Unknown license" in result.output


def test_init_uses_config_defaults(devtoolbox_home, tmp_path):
    devtoolbox_home.mkdir(parents=True, exist_ok=True)
    (devtoolbox_home / "config.yaml").write_text(
        "projinit:\n"
        "  default_lang: python\n"
        "  default_license: mit\n"
        "  default_author: Config Author\n",
        encoding="utf-8",
    )

    target = tmp_path / "configdefaultsproject"
    result = runner.invoke(
        app,
        [
            "--name",
            "configdefaultsproject",
            "--description",
            "uses config defaults",
            "--dir",
            str(target),
            "--no-git",
            "--no-run-init-command",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (target / "requirements.txt").exists()
    license_text = (target / "LICENSE").read_text(encoding="utf-8")
    assert "Config Author" in license_text
