# projarchive

Frees up disk space held by unused projects while keeping them trivially
reproducible later.

- **`archive-project`/`restore-project`** — archiving deletes just the venv
  (after making sure a `requirements.txt` exists, generating one via `pip
  freeze` if it doesn't); restoring rebuilds the venv from that file — via
  `uv` if it's installed, falling back to `python -m venv` + `pip` otherwise.
- **`compress-project`/`restore-compressed-project`** — for projects you
  won't touch for a while, compresses the *whole* project folder to a single
  `.zip`/`.tar.gz` (venv included — archived away first, the same way
  `archive-project` does it) and deletes the original folder once the
  archive is verified. Restoring unpacks it and rebuilds the venv, back to
  a fully working project in one command.

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

# Or, for a project you won't touch for a long time: compress the whole
# folder (venv included) down to one file, freeing nearly all its disk space
projarchive compress-project ~/code/old-course-project

# ...much later, need it again:
projarchive restore-compressed-project ~/code/old-course-project_20260806.zip
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

### `projarchive compress-project PATH [options]`

Compresses `PATH`'s entire contents to a single `.zip`/`.tar.gz` next to it
and deletes the original folder, for projects you don't expect to touch for
a long time.

**Processing flow:**

1. Measure `PATH`'s current total size (this is the "original size" used in
   the final summary — it includes the venv and everything else, before any
   of the steps below touch it).
2. **Large-file scan:** find every file at or above
   `--large-file-threshold-mb` (default 500 MB) — meant to catch datasets,
   model checkpoints, etc. If any are found, they're listed with their
   sizes and you're asked whether to exclude them (`--exclude-large-files`
   / `--include-large-files` answer this upfront instead of prompting; in a
   non-interactive session without one of these flags, the command aborts
   rather than hang). Excluded files are moved to a sibling
   `<project>_excluded/` folder *before* anything is deleted, so choosing
   "exclude" never loses data — `restore-compressed-project` moves them back
   automatically.
3. If a venv (`venv`/`.venv`) is present, it's archived first — exactly like
   `archive-project` (ensure `requirements.txt`, delete the venv). This is
   the biggest space saver, since venv contents compress poorly and are
   fully reproducible from `requirements.txt` anyway. A `pip freeze` failure
   aborts here, before anything is compressed or deleted, same as
   `archive-project`.
4. If no `README.md` exists, a minimal one is generated from the project
   name and its top-level file/folder listing, so a future you can tell
   what the project was at a glance without extracting the archive.
5. The (now venv-free, excluded-file-free) folder is compressed to
   `<project>_<YYYYMMDD>.zip` or `.tar.gz` next to it, at
   `--compression-level standard` (default) or `max` (`--max-compression`
   is a shortcut for `--compression-level max`).
6. **Integrity check:** the freshly-written archive is read back (`zipfile`
   CRC verification / full `tarfile` extraction-to-nowhere) before anything
   is deleted. If this fails, the archive is deleted and the original
   folder (plus any `_excluded` folder) is left exactly as it was — exit 1.
7. Only once verification passes is the original project folder deleted.
8. A metadata row is recorded (see
   [Compressed-project metadata](#compressed-project-metadata-sqlite)
   below) and a before/after size summary is printed.

```
$ projarchive compress-project ~/code/old-course-project --large-file-threshold-mb 200
Found 1 file(s) >= 200 MB:
  data/train.csv  (512.00 MB)
  -> excluding 1 file(s)
Compressed C:\Users\me\code\old-course-project -> C:\Users\me\code\old-course-project_20260808.zip
  original size: 780.40 MB
  compressed size: 45.10 MB
  saved: 735.30 MB (94.2%)
  venv archived first: .venv (230.00 MB freed)
  README.md: auto-generated
  excluded 1 large file(s) -> C:\Users\me\code\old-course-project_excluded
```

`--dry-run` shows the large-file scan and a preview (current size, whether
the venv would be archived, whether a README would be generated) without
compressing, deleting, or writing anything — same non-destructive contract
as `archive-project --dry-run`.

### `projarchive restore-compressed-project ARCHIVE`

Extracts `ARCHIVE` (a `.zip`/`.tar.gz` produced by `compress-project`) back
to its original location and rebuilds it into a fully working project.

**Processing flow:**

1. Look up `ARCHIVE`'s metadata row to know the original project name and
   parent directory (falling back to parsing the filename if the metadata
   DB is unavailable). If a folder already exists at that destination, the
   command refuses to overwrite it — exit 1.
2. Extract the archive there.
3. If large files were excluded at compression time, move them back from
   the `_excluded` folder into the restored project and remove the now-empty
   `_excluded` folder.
4. If the restored project has a `requirements.txt` and no venv (which is
   always true right after extraction, since `compress-project` always
   archives the venv before compressing), rebuild the venv by reusing
   `restore-project`'s exact logic (`uv` if available, else
   `python -m venv` + `pip`). A venv-rebuild failure is reported but doesn't
   fail the whole command — the project is still fully extracted and can be
   retried with `restore-project` directly.
5. The metadata row is updated to `restored`, and elapsed time / venv-rebuild
   outcome are printed.

```
$ projarchive restore-compressed-project ~/code/old-course-project_20260808.zip
Restored C:\Users\me\code\old-course-project
  elapsed: 14.2s
  restored 1 previously-excluded file(s)
  venv: rebuilt (via uv)
```

### `projarchive list-projects PARENT`

Lists every immediate subdirectory of `PARENT` that looks like a project —
i.e. has a venv, a `.archived` marker, or a `requirements.txt` — plus any
project directly under `PARENT` that's been compressed away, in a table:

| Column | Meaning |
|---|---|
| Project | Directory name (or original project name, for compressed entries) |
| Status | `active` (has a venv), `archived` (has `.archived`, no venv), `unarchived` (has `requirements.txt` but no venv and no marker), or `compressed` (folder is gone, an archive from `compress-project` exists) |
| venv size | Total size of the venv directory, or `-` otherwise |
| requirements.txt | `yes` / `no`, or `-` for compressed entries |
| Archive | Compressed entries only: `<filename> (<compressed date>)` |
| Compressed size | Compressed entries only: size of the `.zip`/`.tar.gz` |

Directories with none of venv/marker/`requirements.txt` are left out
entirely, so unrelated folders (notes, data, docs, ...) sitting next to your
projects don't clutter the list. A `compressed` row only shows up while its
archive file still exists on disk and no folder has taken its place again
(e.g. after a manual extraction) — restoring it via
`restore-compressed-project` turns it back into a normal `active`/`archived`
row.

```
$ projarchive list-projects ~/code
                                     Projects under ~/code
+---------------------------------------------------------------------------------------------+
| Project     | Status     | venv size | requirements.txt | Archive                      | Compressed size |
|-------------+------------+-----------+-------------------+------------------------------+-----------------|
| proj_a      | archived   |         - | yes               | -                            |               - |
| proj_b      | active     | 200.00 KB | no                | -                            |               - |
| old_course  | compressed |         - | -                 | old_course_20260806.zip (...) |         45.10 MB |
+---------------------------------------------------------------------------------------------+
```

If `PARENT` isn't a directory, exits 1. If it has no matching subdirectories
and no compressed entries, prints "No projects found under PARENT" and exits
0.

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

## Compressed-project metadata (SQLite)

Unlike archiving, compressing a project deletes the folder entirely, so
there's nowhere left to put a marker file — instead, `compress-project` and
`restore-compressed-project` record one row per compression in a SQLite DB
at `~/.devtools/compressed_projects.db` (relocatable via the
`PROJARCHIVE_HOME` env var, mainly used by the test suite), table
`compressions`:

| Column | Meaning |
|---|---|
| `project_name`, `parent_dir` | Original project name and its parent directory (absolute path) |
| `archive_path` | Absolute path to the `.zip`/`.tar.gz` |
| `format`, `compression_level` | `"zip"`/`"tar.gz"`, `"standard"`/`"max"` |
| `compressed_at` | UTC timestamp (ISO 8601) |
| `original_size_bytes`, `compressed_size_bytes` | Sizes before/after |
| `venv_stripped`, `venv_dir_name` | Whether a venv was archived away first, and its folder name |
| `excluded_files` | JSON list of `{"path": ..., "size_bytes": ...}` for large files moved to `_excluded/` |
| `excluded_dir` | Path to that `_excluded/` folder, if any |
| `status` | `"compressed"` or `"restored"` |
| `restored_at`, `restore_elapsed_seconds` | Set once `restore-compressed-project` runs |
| `restore_venv_rebuilt`, `restore_used_uv` | Whether/how the venv was rebuilt on restore |

`restore-compressed-project` looks up this table by `archive_path` to know
where to extract to and which `_excluded/` folder to merge back in. If the
row is missing (DB moved/lost, or the archive came from another machine), it
falls back to parsing the project name out of the filename
(`<name>_<YYYYMMDD>.<ext>`) and extracts next to the archive instead.
`list-projects` reads this table to show `compressed` rows, filtering to
records whose archive file still exists on disk and whose `status` is still
`"compressed"`.

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
- `compress-project` excludes large files by *moving* them to a sibling
  `_excluded/` folder before deleting anything, never by dropping them —
  they're restored automatically by `restore-compressed-project`.
- The original project folder is only deleted after the freshly-written
  archive has been read back and verified. A failed integrity check deletes
  the bad archive instead and leaves the original folder (and any
  `_excluded/` folder) untouched.
- `restore-compressed-project` refuses to extract over an existing folder at
  the destination rather than overwriting it.
- A venv-rebuild failure during `restore-compressed-project` is reported but
  doesn't fail the command — the extracted project is left in place and can
  be retried with `restore-project` directly.

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests mock out `pip freeze`, `uv venv`/`uv pip install`, and
`python -m venv` (via `subprocess.run` / `shutil.which`) — nothing actually
shells out during the test suite. Compression/restore tests redirect the
metadata DB via the `PROJARCHIVE_HOME` env var (the `projarchive_home`
fixture) so they never touch the real `~/.devtools`.
