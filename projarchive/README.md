# projarchive

Frees up disk space held by unused project venvs (often hundreds of MB to a
few GB each) while keeping them trivially reproducible later: archiving
deletes the venv but first makes sure a `requirements.txt` exists (generating
one via `pip freeze` if it doesn't), and restoring rebuilds the venv from
that file — via `uv` if it's installed, falling back to `python -m venv` +
`pip` otherwise.

## Install

```bash
cd projarchive
pip install -e ".[dev]"
```

From GitHub (this package lives in the `projarchive/` subdirectory of the repo):

```bash
pip install "git+https://github.com/noza-kit/devtools.git#subdirectory=projarchive"
```

## Quick start

```bash
# See what's eating disk space across a folder of old projects
projarchive list-projects ~/code

# Preview one archive before committing to it
projarchive archive-project ~/code/old-course-project --dry-run

# Actually archive it (deletes the venv, keeps requirements.txt)
projarchive archive-project ~/code/old-course-project

# ...months later, need it again:
projarchive restore-project ~/code/old-course-project
```

## Commands

### `projarchive archive-project PATH [--all] [--dry-run]`

Deletes `PATH`'s venv after making sure its dependencies are captured in
`requirements.txt`.

**Processing flow (single project):**

1. Look for a venv under `PATH`, checking `venv` first, then `.venv`. If
   neither exists → error, exit 1, nothing is touched.
2. Check whether `requirements.txt` already exists at the project root.
   - If yes, use it as-is.
   - If no, run `<venv>/Scripts/pip.exe freeze` (Windows) or
     `<venv>/bin/pip freeze` (Mac/Linux) and write the output to
     `requirements.txt`. **If this fails for any reason (broken venv,
     missing pip binary, ...), the command aborts with an error and exits
     1 — the venv is *not* deleted.** This is the safety net: archiving
     never destroys a venv it wasn't able to capture first.
3. Delete the venv directory (`shutil.rmtree`).
4. Write a `.archived` marker file at the project root (see
   [Marker file format](#archived-marker-file-format) below).
5. Print a summary: how much space was freed, and whether
   `requirements.txt` was generated just now or already existed.

Re-running `archive-project` on a project that already has a `.archived`
marker fails with "already archived" (exit 1) rather than silently
re-archiving.

**Example:**

```
$ projarchive archive-project ~/code/old-course-project
Archived C:\Users\me\code\old-course-project
  venv freed: 312.40 MB (.venv)
  requirements.txt: generated via `pip freeze`
```

**`--all` — batch mode:** treats `PATH` as a *parent* directory and archives
every immediate subdirectory that looks like a project (i.e. has a venv).
Each project is archived independently — one project's failure (e.g. a
broken venv where `pip freeze` errors out) only skips that project and
prints why; it doesn't abort the batch. A subdirectory with neither a venv
nor a `.archived` marker is skipped as "no venv found". A summary line is
printed at the end. Exit code is always 0 for `--all` (per-project failures
are reported, not fatal).

```
$ projarchive archive-project ~/code --all
skip notes: no venv found
archived proj_a: 100.00 KB (existing requirements.txt)
skip proj_b: pip freeze failed for .../proj_b: [WinError 2] ...

1 project(s) archived, 2 skipped, 100.00 KB freed total
```

**`--dry-run` — preview only:** reports the venv size and whether
`requirements.txt` would be generated, **without invoking pip, deleting the
venv, or writing the marker file.** Combine with `--all` to preview a whole
batch. Output is prefixed with `[dry-run]`:

```
$ projarchive archive-project ~/code/old-course-project --dry-run
[dry-run] would archive C:\Users\me\code\old-course-project
  venv would free: 312.40 MB (.venv)
  requirements.txt: would be generated via `pip freeze`
```

### `projarchive restore-project PATH`

Rebuilds `PATH`'s venv from `requirements.txt`.

**Processing flow:**

1. Check `requirements.txt` exists at `PATH` → error, exit 1, if missing.
2. Check whether a venv (`venv` or `.venv`) already exists → if so, print
   "already restored" and exit 0 without doing anything (idempotent, safe
   to re-run).
3. Check whether the `uv` command is on `PATH`:
   - **If available:** run `uv venv` (creates `.venv`), then
     `uv pip install -r requirements.txt`.
   - **If not available:** fall back to `python -m venv venv` (creates
     `venv`), then install with that venv's own `pip`.
   - If either command fails, the restore aborts with an error, exit 1, and
     the `.archived` marker is left in place (so a failed restore can be
     retried).
4. On success, remove the `.archived` marker.
5. Print the elapsed time.

**Example:**

```
$ projarchive restore-project ~/code/old-course-project
Restored C:\Users\me\code\old-course-project
  venv: venv (via python -m venv + pip)
  elapsed: 13.8s
```

Note the venv folder name can differ from what was archived: `uv venv`
always creates `.venv`, while the `python -m venv` fallback always creates
`venv`, regardless of what the project had before. This doesn't cause
problems for `projarchive` itself (`archive-project`/`list-projects` look
for both names), but if you have scripts/IDE configs hardcoded to one name,
be aware a restore can change it.

### `projarchive list-projects PARENT`

Lists every immediate subdirectory of `PARENT` that looks like a project —
i.e. has a venv, a `.archived` marker, or a `requirements.txt` — in a table:

| Column | Meaning |
|---|---|
| Project | Directory name |
| Status | `active` (has a venv), `archived` (has `.archived`, no venv), or `unarchived` (has `requirements.txt` but no venv and no marker — e.g. cloned fresh, or the marker was deleted manually) |
| venv size | Total size of the venv directory, or `-` if archived/unarchived |
| requirements.txt | `yes` / `no` |

Directories with none of the three (venv, marker, or `requirements.txt`) are
left out entirely, so unrelated folders (notes, data, docs, ...) sitting
next to your projects don't clutter the list.

```
$ projarchive list-projects ~/code
                  Projects under ~/code
+-------------------------------------------------+
| Project | Status   | venv size | requirements.txt |
|---------+----------+-----------+------------------|
| proj_a  | archived |         - | yes              |
| proj_b  | active   | 200.00 KB | no               |
+-------------------------------------------------+
```

If `PARENT` isn't a directory, exits 1. If it has no matching
subdirectories, prints "No projects found under PARENT" and exits 0.

## `.archived` marker file format

Written to `<project>/.archived` as JSON when a project is archived, and
deleted when it's restored:

```json
{
  "archived_at": "2026-08-06T14:47:10.011306+00:00",
  "venv_dir_name": ".venv"
}
```

- `archived_at` — UTC timestamp (ISO 8601) of when `archive-project` ran.
- `venv_dir_name` — the folder name (`venv` or `.venv`) the venv had *before*
  it was deleted. Currently informational only (restore always creates
  `.venv` via `uv` or `venv` via the `python -m venv` fallback, regardless
  of this value) — kept in the marker so a human (or a future feature) can
  tell what the original layout was.

Its mere presence is what `list-projects` and `restore-project` use to
recognize a project as archived; there's no separate "archived" flag file.

## Safety guarantees

- `archive-project` never deletes a venv unless `requirements.txt` is
  confirmed to exist (pre-existing or freshly generated). A `pip freeze`
  failure aborts before any deletion.
- `--dry-run` never calls pip, never deletes, never writes the marker or
  `requirements.txt` — it's a pure preview.
- `--all` isolates failures per-project; one broken project doesn't stop the
  rest of the batch from being archived.
- `restore-project` only clears the `.archived` marker after the venv is
  fully created *and* `pip install`/`uv pip install` has succeeded — a
  failed restore leaves the marker in place so it's obviously still
  "archived" and safe to retry.
- Re-archiving an already-archived project, or restoring a project that
  already has a venv, are both rejected/no-ops rather than silently
  overwriting anything.

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests mock out `pip freeze`, `uv venv`/`uv pip install`, and
`python -m venv` (via `subprocess.run` / `shutil.which`) — nothing actually
shells out during the test suite.
