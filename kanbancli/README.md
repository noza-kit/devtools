# kanbancli

An offline, Markdown-file-backed task list. The file itself (plain text,
one task per line) is the single source of truth — no database, no
proprietary format, fully portable and readable/editable by hand.

- [Install](#install)
- [File resolution (hybrid local/global)](#file-resolution-hybrid-localglobal)
- [Task line format](#task-line-format)
- [Status tokens](#status-tokens)
- [Commands](#commands)
- [Due-date reminders](#due-date-reminders)
- [Migrating from devtoolbox's `todo`](#migrating-from-devtoolboxs-todo)
- [Known limitations](#known-limitations)
- [Development](#development)

## Install

```bash
cd kanbancli
pip install -e "../notify"    # local dependency, not on PyPI
pip install -e ".[dev]"
```

## File resolution (hybrid local/global)

Every command accepts `--file`/`-f` to name a task file explicitly.
Without it:

1. Look for `.kanban.md` in the current directory, then its parents
   (project-local task list — handy for a `.kanban.md` committed
   alongside a repo).
2. If none is found anywhere up the tree, fall back to the global
   `~/.config/kanbancli/tasks.md` (created on first write).

```bash
cd ~/projects/my-app
kanbancli add "Fix the thing"   # writes to ~/projects/my-app/.kanban.md if it exists,
                                 # else ~/projects/.kanban.md, ~/.kanban.md, ...,
                                 # else ~/.config/kanbancli/tasks.md
```

## Task line format

```
- [status] task content [priority] @add:YYYY-MM-DD @due:YYYY-MM-DD @recur:1w @depends:x7a9 #tag id:g7h8
```

```markdown
- [~] データベースのテーブル設計 [!!] @add:2026-08-01 @due:2026-08-10 #database id:x7a9
- [iii] 外部APIの調査 [!] @add:2026-08-06 id:a1b2
  - [x] APIキーの取得 id:c3d4
  - [ ] エンドポイントのテスト id:e5f6
- [ ] バックエンドの実装 [!!!] @depends:x7a9 @depends:a1b2 id:g7h8
```

Everything after `[status]` and the task content is parsed
order-independently (each `@key:value`/`#tag`/`[priority]`/`id:` token
is found by its own pattern, not by position), so you can freely
reorder attributes by hand without breaking anything — the only fixed
positions are `[status]` right after `- ` and `id:xxxx` being how the
line is definitively recognized as a task at all (a line with no
`id:xxxx` raises a parse error; a line that doesn't start with `- [` is
just silently treated as a non-task line and skipped — kanbancli
doesn't currently preserve arbitrary Markdown prose/comments around the
task list on save, see [Known limitations](#known-limitations)).

- **Priority**: `[!]`, `[!!]`, `[!!!]` (0-3 "!"s; omitted = no priority).
- **Dates**: `@add:YYYY-MM-DD` (set automatically by `add`), `@due:YYYY-MM-DD`.
- **Recurrence**: `@recur:1d`/`2w`/`1m`/`1y` (days/weeks/months/years).
  See [Commands](#commands)'s `update` for what happens on completion.
- **Tags**: `#tagname`, repeatable.
- **Dependencies**: `@depends:id`, repeatable — the task is treated as
  blocked (for `list --available`'s filtering, not enforced against
  manual status changes) until every referenced id is `done`. A
  `@depends:id` pointing at an id that no longer exists in the file
  (e.g. its target was archived) does **not** count as blocking —
  otherwise archiving a dependency would leave its dependents
  permanently stuck.
- **Subtasks**: indentation (2 or 4 spaces) below a parent line. Levels
  are always computed as `indent_width // 2` — a file consistently
  using 4 spaces per level still nests correctly (each deeper line
  still gets a strictly larger level number than its parent, which is
  all that actually matters for the tree/blocking/insertion logic),
  just with level numbers double what a 4-space-per-level author might
  expect. Tabs are expanded to 4 spaces before measuring.
- **id**: a 4-character lowercase-alphanumeric short id, auto-assigned
  by `add` (regenerated on the rare collision).

## Status tokens

| Token | Meaning |
| --- | --- |
| `[ ]` | Not started |
| `[~]` or `[/]` | In progress (no specific percentage) |
| `[i]` … `[ix]` | In progress, 10%–90% (Roman numerals i=1 through ix=9, ×10%) |
| `[x]` | Done (Roman numeral for 10 — the same symbol family as the `[i]`-`[ix]` progress tokens, extended to "fully done") |
| `[-]` | Cancelled |
| `[>]` | Postponed |

`kanbancli update` also accepts friendly aliases instead of raw tokens:
`todo`, `start`/`doing`, `done`/`complete`, `cancel`/`cancelled`,
`postpone`/`postponed`, and `10`/`20`/.../`90` for the percentage
tokens.

## Commands

### `kanbancli add`

```bash
kanbancli add "API調査" --due 2026-08-10 --priority ! --tags backend,api
kanbancli add "サブタスク" --parent x7a9
kanbancli add "週次レポート提出" --due 2026-08-07 --recur 1w
kanbancli add                                    # no content -> interactive prompt
```

`--parent ID` inserts the new task as a subtask (indented, `level =
parent.level + 1`) immediately after its parent (and after any of the
parent's existing subtasks). `--recur` is validated immediately (fails
fast) rather than only failing later when the task is eventually
completed.

### `kanbancli update`

```bash
kanbancli update x7a9 done
kanbancli update x7a9 x        # same thing, raw token
kanbancli update x7a9 50       # -> [v] 50%
```

Completing (`done`) a task that has `@recur` appends a fresh copy with
a new id, `status=[ ]`, and `@due` advanced by the recur interval —
**from the original `@due`, not from today's completion date** — so a
"every Friday" weekly task stays anchored to Fridays even if actually
marked done a few days early or late.

### `kanbancli list`

```bash
kanbancli list
kanbancli list --sort priority
kanbancli list --sort due
kanbancli list --available          # only unblocked, not-yet-done/cancelled tasks
kanbancli list --tag backend
kanbancli list --status in_progress # todo | in_progress | progress | done | cancelled | postponed
```

### `kanbancli export`

```bash
kanbancli export today.md --due-before 2026-08-08
kanbancli export work.md --tags work,urgent
```

Writes a filtered subset of tasks to a separate Markdown file (same
line format, so it's a fully valid kanbancli file on its own).

### `kanbancli archive`

```bash
kanbancli archive
kanbancli archive --archive-path ./done-2026.md
```

Moves every `done`/`cancelled` task out of the main file into an
archive file (default: `archive.md` next to the main file), appending
to whatever's already there. A completed parent task does **not** force
its still-open subtasks to archive too — each task's own status decides
independently.

## Due-date reminders

```bash
kanbancli remind                              # one-shot check, sends a notify() if anything's due
kanbancli remind --within-days 7 --channels discord,desktop

kanbancli setup-autostart                     # daily Task Scheduler job, 09:00, desktop channel
kanbancli setup-autostart --time 08:00 --channels discord --within-days 1
kanbancli setup-autostart --remove
```

`remind` sends **one** `notify()` call summarizing every task that's
overdue or due within `--within-days` (default 3) days, or does nothing
if there's nothing to report. `setup-autostart` registers a Windows
Task Scheduler task with a **daily** trigger (not just at-logon, since a
due-date check should fire on a schedule even across a session that's
stayed logged in for days) running `kanbancli remind`; `--rl LIMITED`
means no admin rights are needed, same as [`sysreport`](../sysreport)'s
autostart registration, which this mirrors.

## Migrating from devtoolbox's `todo`

kanbancli supersedes [devtoolbox](../devtoolbox)'s SQLite-backed `todo`
command (see devtoolbox's README) — richer feature set (priority, due
dates, recurrence, dependencies, subtasks, reminders), plain-text
storage instead of a database. `todo` itself is untouched and still
works; there's no automatic data-migration command from `todo.db` to a
kanbancli file in this round; recreate a handful of tasks by hand.

## Known limitations

- **No round-trip preservation of non-task content.** A file loaded and
  saved by kanbancli keeps only recognized task lines — a `#
  Introduction` heading, blank-line spacing, or hand-written notes
  interleaved with tasks won't survive an `add`/`update`/etc. that
  rewrites the file. Keep prose in a separate file if you want both.
- **Dependencies don't block manual status changes.** `@depends`
  affects `list --available`'s filtering only; nothing stops `update
  ID done` on a task that's still technically blocked. This was a
  deliberate choice (per the spec's own wording, "treated as blocked"
  for listing purposes, not "prohibited") rather than an oversight.
- **Archiving a parent doesn't cascade to its subtasks** (see
  [`archive`](#kanbancli-archive) above) — intentional, but worth
  knowing if you expected a whole subtree to move together.

## Development

```bash
pip install -e "../notify"
pip install -e ".[dev]"
pytest
```

Tests build task files directly (via `Task`/`format_line`, or through
`ops.add_task` etc.) rather than depending on fixture `.md` files.
`notify()` is monkeypatched in `test_remind.py`/`test_cli.py` (see
`feedwatch`'s tests for the same pattern used elsewhere in this repo);
`schtasks` is monkeypatched in `test_autostart.py` — nothing shells out
or sends a real notification during the test suite.
