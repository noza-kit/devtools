# diskcheck

A storage management CLI with three independent subcommands: rank folders by
size, find duplicate files by content, and flag old installers/temp files for
manual cleanup. Every feature defaults to "show candidates only" — nothing is
ever deleted without an explicit interactive confirmation or `--yes`.

## Install

```bash
cd diskcheck
pip install -e ".[dev]"
```

From GitHub (this package lives in the `diskcheck/` subdirectory of the repo):

```bash
pip install "git+https://github.com/noza-kit/devtools.git#subdirectory=diskcheck"
```

## Usage

### `diskcheck scan` — storage usage ranking

```bash
diskcheck scan ~/Downloads --top 20 --depth 2
diskcheck scan ~/Downloads --json
diskcheck scan ~/Downloads --interactive
```

- Recursively scans `PATH`, aggregating directory sizes bottom-up, and prints
  a tree showing the top `--top` largest entries per level (down to `--depth`
  levels), with each folder's total size shown alongside it.
- `--json` emits the same tree as machine-readable JSON instead.
- `--interactive` / `-i` drops into a drill-down browser instead: pick a
  numbered subfolder to descend into, `u` to go back up, `q` to quit.
- Unreadable entries (permission errors, broken links) are skipped rather
  than aborting the scan; symlinked directories are recorded by their own
  size rather than followed, to avoid double-counting and symlink loops.

### `diskcheck dupes` — duplicate file detection

```bash
diskcheck dupes ~/Downloads
diskcheck dupes ~/Downloads --json
diskcheck dupes ~/Downloads --interactive --yes
```

- Recursively scans `PATH` and groups files with identical content. For
  performance, files are first bucketed by size (cheap `stat` call); only
  files that share a size with at least one other file get their SHA256
  hashed (in parallel, via a thread pool), so unique-sized files never pay
  the hashing cost.
- Groups are sorted by reclaimable space (`size * (copies - 1)`) descending,
  and each file is shown with its last-modified time.
- Default mode is a dry run: it only lists duplicate groups, nothing is
  deleted. Add `--interactive` / `-i` to go through each group and choose
  which copy to keep (default: the newest); every other copy in the group is
  deleted after a per-group confirmation (skip with `--yes`).
- `--min-size` ignores files below a byte threshold (default: 1, so empty
  files are never compared).

### `diskcheck stale` — old installer / temp file candidates

```bash
diskcheck stale ~/Downloads --older-than 180
diskcheck stale ~/Downloads --extensions .dmg,.exe,.iso --older-than 90
diskcheck stale ~/Downloads --config ./diskcheck.yaml
```

- Finds files under `PATH` whose extension matches a configured list
  (default: `.dmg .exe .msi .pkg .deb .AppImage`) and whose last-access time
  is at least `--older-than` days ago (default: 180). Results are sorted by
  size descending, so the most impactful cleanup candidates are listed
  first.
- `--extensions` takes a comma-separated list that overrides the config/
  default list for a single run.
- `--config` points at a YAML/JSON config file (loaded via the `confload`
  package) with a top-level `extensions` list:

  ```yaml
  extensions:
    - .dmg
    - .exe
    - .iso
  ```

- This command never deletes anything — it only prints a list (or `--json`)
  for you to review and clean up manually.

## Development

```bash
pip install -e ".[dev]"
pytest
```
