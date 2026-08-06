# translate-comments

CLI that translates source code comments between Japanese, English, and
French via [DeepL](https://www.deepl.com/pro-api), without touching the code
itself.

## Install

```bash
cd translate-comments
pip install -e ".[dev]"
```

This package depends on two sibling packages in this repo, `reqretry` (HTTP
retries) and `confload` (config loading). Install them too, in editable mode:

```bash
pip install -e ../reqretry -e ../confload
```

### Getting a DeepL API key

1. Go to [deepl.com/pro-api](https://www.deepl.com/pro-api) and click **Sign
   up for free** (the free tier — 500,000 characters/month — is enough for
   this tool; a credit card is required at signup even for the free plan,
   but you won't be charged unless you explicitly upgrade).
2. After signing up/logging in, open the
   [Account page](https://www.deepl.com/account/summary) → **API keys** tab.
3. Copy the key shown there. A free-tier key always ends in `:fx`
   (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:fx`); a paid Pro key has no
   suffix — `translate_comments` picks the correct API endpoint
   (`api-free.deepl.com` vs `api.deepl.com`) automatically based on whether
   the key ends in `:fx`.

Set it as an environment variable:

```bash
export DEEPL_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:fx  # a ":fx" suffix means a free-tier key
```

Or in a `confload` YAML/JSON file passed via `--config` (see the `--config`
row in [Options](#options) below):

```yaml
# secrets.yaml
deepl_api_key: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:fx
```

## Usage

```bash
translate-comments app.py --from ja --to en,fr
```

Preview only, without calling DeepL or writing anything:

```bash
translate-comments ./src --from ja --to en --recursive --dry-run
```

Process a whole directory, skipping the confirmation prompt:

```bash
translate-comments ./src --from ja --to en,fr --recursive --yes
```

### Options

| Option | Meaning |
| --- | --- |
| `PATH` | A single file, or a directory to scan for supported source files |
| `--from` | Source language: `ja`, `en`, or `fr` |
| `--to` | Target language(s), comma-separated, e.g. `en,fr` |
| `--mode` | `inline` (default), `separate`, or `replace` — see below |
| `--recursive` | When `PATH` is a directory, recurse into subdirectories |
| `--dry-run` | Show the comment preview; never calls DeepL or writes files |
| `--yes` / `-y` | Skip the confirmation prompt |
| `--config` | A confload YAML/JSON file to read `deepl_api_key` from, instead of `DEEPL_API_KEY` |

Every run first prints a preview of the comments/docstrings that will be
translated (file, line range, style, and a text snippet) and asks for
confirmation before calling DeepL — unless `--dry-run` (stops after the
preview) or `--yes` (skips the prompt) is given.

### `--mode inline`

Appends each translation directly below the original comment, in the file
itself. A comment translated into more than one language gets one line per
language, tagged so multiple translations don't run together:

```python
# 挨拶を作る
# [EN] Build the greeting
# [FR] Construire le message d'accueil
msg = "Hello, " + name
```

A trailing comment (`code  # comment`) gets a new comment-only line inserted
right after it, matching the code's indentation. A block comment (`/* */`)
gets a new block comment appended the same way. A Python docstring is a
special case: since only the first bare string literal in a
module/class/function is semantically "the" docstring, its translation is
appended as a `#` comment rather than a second (meaningless) string-literal
statement.

### `--mode separate`

Leaves the original file untouched and writes one full copy per target
language, with each comment/docstring **replaced** by its translation (code
is otherwise identical). `app.py` + `--to en,fr` produces `app_en.py` and
`app_fr.py` alongside `app.py`. A docstring keeps its original quote style
(`"""`, `'''`, an `r"""` prefix, etc.) with just the text swapped in, so the
result is still a valid docstring.

### `--mode replace`

Same replacement as `separate`, but written back to the original file itself
instead of a per-language copy — the original-language comment text is
gone once this runs (recover it from version control if you need it).
Because it overwrites a single file, it only accepts one `--to` language at
a time; a comma-separated list is rejected. A yellow warning is printed
before the confirmation prompt as a reminder that this is destructive.

```bash
translate-comments app.py --from ja --to en --mode replace
```

## Comment extraction

`translate_comments.extract_comments(path)` reads a source file and returns a
list of `CommentBlock`s — the comments (and, for Python, docstrings) found in
it. The code around them is never modified; only comment/docstring text is
extracted.

Supported comment syntax, matched by file extension:

| Extension(s) | Line comment | Block comment | Docstrings |
| --- | --- | --- | --- |
| `.py`, `.pyw` | `#` | — | yes (`ast`-based) |
| `.sh`, `.bash`, `.zsh` | `#` | — | — |
| `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`, `.cjs`, `.c`, `.h`, `.cpp`, `.cc`, `.hpp`, `.cs`, `.java`, `.go`, `.rs`, `.kt`, `.swift` | `//` | `/* */` | — |

```python
from translate_comments import extract_comments

for block in extract_comments("app.py"):
    print(block.style, block.start_line, block.text)
```

Notes on what counts as a comment:

- Comment markers inside string literals are ignored (best-effort string
  masking via single-pass scanning, not a full parser). Known limitations:
  backslash-escaping inside raw/verbatim strings (e.g. C# `@"..."`) isn't
  modeled, and JS template-literal `${...}` interpolations are treated as
  opaque string content.
- Adjacent standalone `#`/`//` comment lines (same indent, no gap) are merged
  into one `CommentBlock` so they get translated together, with more context.
  A trailing comment (code precedes it on the same line) is never merged
  with neighboring lines.
- Shebang lines (`#!...` on line 1) and PEP 263 encoding declarations
  (`# -*- coding: ... -*-`) are excluded.
- Comments with no alphabetic content (e.g. `# ----------`) are excluded.
- Python docstrings are detected via `ast` (a string literal that is the
  sole first statement of a module/class/function), not by scanning for
  `"""`/`'''`, since those are ordinary string-literal syntax and only mean
  "docstring" in that specific position.

## DeepL API calls

All requests to DeepL go through `reqretry`, so timeouts, connection errors,
5xx responses, and 429 (rate limited) are retried with exponential backoff.
Comments across an entire run are batched into one DeepL request per target
language (not one request per comment), to keep API usage efficient.

## Development

```bash
pip install -e ../reqretry -e ../confload -e ".[dev]"
pytest
```

Tests use [`responses`](https://github.com/getsentry/responses) to mock the
DeepL API and monkeypatch `time.sleep` so retry backoff is verified without
real network calls or real waiting.
