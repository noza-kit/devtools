# devtoolbox

Personal CLI toolbox, packaged as a single pip-installable package with five
tools:

- **`projinit`** — scaffold a new project (`git init`, `.gitignore`, `README.md`, `LICENSE`)
- **`snip`** — save, search, and recall code snippets from the terminal
- **`todo`** — a personal task list
- **`dotsync`** — symlink dotfiles from a source repo into `$HOME`
- **`doctor`** — dump a system/environment report (OS, CPU, memory, GPU, git, Python) for reproducibility notes

## Install

### From this local checkout (editable install for development)

```bash
cd devtoolbox
pip install -e ".[dev]"
```

### From GitHub

This package lives in the `devtoolbox/` subdirectory of the repo, so install
with pip's `subdirectory` fragment:

```bash
pip install "git+https://github.com/noza-kit/devtools.git#subdirectory=devtoolbox"
```

After installing, the `projinit`, `snip`, `todo`, `dotsync`, and `doctor`
commands are available directly on your PATH. All support shell completion —
run `<command> --install-completion` to enable it.

## `projinit`

Scaffold a new project directory with `git init`, a language-appropriate
`.gitignore`, a `README.md`, an optional `LICENSE`, and the language's init
command (`python -m venv .venv`, `npm init -y`, ...).

```bash
# fully via flags
projinit --name myproject --lang python --description "my new project" --license mit

# omit flags to be prompted interactively
projinit
```

Options:

| Flag | Description |
| --- | --- |
| `--name`, `-n` | Project name |
| `--lang`, `-l` | Language/framework key (`python`, `node`, `generic`, ...) |
| `--description`, `-d` | Short description embedded in the README |
| `--dir` | Target directory (default: `./<name>`) |
| `--git` / `--no-git` | Run `git init` (default: on) |
| `--run-init-command` / `--no-run-init-command` | Run the language's init command, e.g. venv creation or `npm init` (default: on) |
| `--license`, `-L` | License key: `mit`, `apache-2.0`. Omitted → no `LICENSE` file |
| `--author`, `-a` | Copyright holder for the `LICENSE` file (default: `git config user.name`, else `Unknown`) |

Existing files are never overwritten — `projinit` reports them as skipped.
If a language's init command fails or the tool isn't installed (e.g. `npm`
missing), it's reported as a warning and the rest of the scaffolding still
runs.

### Adding a new language

Edit `src/devtoolbox/projinit/templates/languages.yaml` and add a
`templates/gitignore/<key>.gitignore` file. Each language entry supports:

- `display_name`, `gitignore` — required
- `init_command` — optional list of argv to run in the new project directory
- `extra_files` — optional list of `{path, content}` (content is a Jinja2
  template rendered with `project_name` and `description`)

No code changes required.

### Adding a new license

Add a Jinja2 template at `templates/license/<Name>.txt` (rendered with `year`
and `author`) and register it in the `LICENSES` dict in
`src/devtoolbox/projinit/config.py`.

## `snip`

A local snippet manager backed by SQLite at `~/.devtools/snippets.db`.

```bash
# save the current clipboard contents
snip add my-snippet --tags python,util

# save from stdin instead of the clipboard
cat script.py | snip add my-snippet --tags python

# edit an existing snippet in $EDITOR (or $VISUAL)
snip edit my-snippet
snip edit my-snippet --tags new,tags        # also replace its tags

# list snippets, optionally filtered by tag (repeat --tag to require all of them)
snip list
snip list --tag python
snip list --tag python --tag util

# list all tags in use, with counts
snip tags

# show a snippet, optionally copying it to the clipboard
snip get my-snippet
snip get my-snippet --copy

# full-text search across name, tags, and content
snip search keyword

# delete a snippet
snip rm my-snippet

# back up / restore snippets as JSON
snip export --output backup.json
snip import backup.json                     # skips names that already exist
snip import backup.json --overwrite          # ...unless --overwrite is given
```

## `todo`

A personal task list backed by SQLite at `~/.devtools/todo.db`.

```bash
todo add "write report" --tags work
todo add "buy milk" --tags errand

# pending tasks only by default; --all includes completed ones
todo list
todo list --all
todo list --tag work                # repeat --tag to require all of them

todo done 1
todo undone 1
todo rm 1

# export as a Markdown checklist (writes ./TODO.md by default, includes done tasks)
todo export
todo export --output notes/TODO.md
todo export --pending-only            # leave out completed tasks
todo export --tag work                # only tasks matching every given tag
```

## `dotsync`

Symlinks dotfiles from a source repo (default `~/dotfiles`, or
`--source`/`dotsync.source_dir` in the config) into `$HOME`. Only top-level
entries whose name starts with `.` are treated as dotfiles — this keeps repo
housekeeping files like `README.md` out of your home directory without an
ignore list, so a dotfiles repo just needs `.bashrc`, `.gitconfig`,
`.config/`, etc. at its root.

```bash
dotsync link                        # symlink everything from ~/dotfiles into $HOME
dotsync link --source ~/my-dotfiles
dotsync link --force                # back up conflicting files to <name>.bak and replace them

dotsync status                      # linked / missing / conflict per entry
dotsync unlink                      # remove the symlinks, restoring any .bak backups
```

Existing files that aren't already the right symlink are left alone and
reported as a conflict unless `--force` is given.

> **Windows note:** creating symlinks requires Developer Mode enabled (or
> running as Administrator). Without it, `dotsync link` will report an
> error for each entry.

## `doctor`

Prints a system/environment report — handy to paste into an experiment's
"how to reproduce this" notes (OS, Python, CPU/memory via `psutil`, GPU via
`nvidia-smi`/OS tools, and the current git repo's branch/commit if run
inside one).

```bash
doctor                              # human-readable report to stdout
doctor --json                       # machine-readable JSON
doctor --output report.txt          # write to a file instead of stdout
doctor --pip                        # also include `pip freeze`
doctor --no-gpu                     # skip GPU detection (it shells out to nvidia-smi/OS tools)
```

GPU detection tries `nvidia-smi` first, then falls back to a platform tool
(PowerShell's `Get-CimInstance` on Windows, `lspci` on Linux,
`system_profiler` on macOS). If none are available, the GPU section is
reported empty rather than failing the command.

## Config

`projinit`, `snip`, and `dotsync` read optional defaults from
`~/.devtools/config.yaml` (the directory can be relocated via the
`DEVTOOLBOX_HOME` env var, mainly used by the test suite):

```yaml
projinit:
  default_lang: python
  default_license: mit
  default_author: Your Name

snip:
  default_tags: [inbox]

dotsync:
  source_dir: ~/my-dotfiles
```

- `projinit.default_lang` / `default_license` / `default_author` are used
  whenever the matching flag is omitted.
- `snip.default_tags` are merged into every `snip add` call automatically.
- `dotsync.source_dir` overrides the default `~/dotfiles` source directory
  whenever `--source` is omitted.

## Development

```bash
pip install -e ".[dev]"
pytest
```
