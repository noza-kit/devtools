# devtoolbox

Personal CLI toolbox, packaged as a single pip-installable package with two
tools:

- **`projinit`** — scaffold a new project (`git init`, `.gitignore`, `README.md`)
- **`snip`** — save, search, and recall code snippets from the terminal

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

After installing, the `projinit` and `snip` commands are available directly
on your PATH.

## `projinit`

Scaffold a new project directory with `git init`, a language-appropriate
`.gitignore`, and a `README.md`.

```bash
# fully via flags
projinit --name myproject --lang python --description "my new project"

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

Existing files are never overwritten — `projinit` reports them as skipped.

### Adding a new language

Edit `src/devtoolbox/projinit/templates/languages.yaml` and add a
`templates/gitignore/<key>.gitignore` file. No code changes required.

## `snip`

A local snippet manager backed by SQLite at `~/.devtools/snippets.db`.

```bash
# save the current clipboard contents
snip add my-snippet --tags python,util

# save from stdin instead of the clipboard
cat script.py | snip add my-snippet --tags python

# list snippets (optionally filtered by tag)
snip list
snip list --tag python

# show a snippet, optionally copying it to the clipboard
snip get my-snippet
snip get my-snippet --copy

# full-text search across name, tags, and content
snip search keyword

# delete a snippet
snip rm my-snippet
```

## Development

```bash
pip install -e ".[dev]"
pytest
```
