# sitewatch

Watch a specific element on a page (by CSS selector) for changes, for sites
that don't offer RSS. Fetches the element via
[BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/), hashes its
text, and sends a [`notify`](../notify) notification when the hash changes
from the previous check. Companion to [`feedwatch`](../feedwatch), which
covers sites that *do* have RSS/Atom feeds (plus Twitch, via a separate
API-based path).

## Install

```bash
cd sitewatch
pip install -e ../reqretry -e ../confload -e ../notify   # local deps, not on PyPI
pip install -e ".[dev]"
```

From GitHub (this package lives in the `sitewatch/` subdirectory of the repo):

```bash
pip install "git+https://github.com/noza-kit/devtools.git#subdirectory=sitewatch"
```

## Quick start

```bash
sitewatch add "https://example.com/product/123" --selector "#price" --name "Widget price"
sitewatch list
sitewatch start                # Ctrl+C to stop
```

## Command reference

| Command | Arguments | Options | Description |
| --- | --- | --- | --- |
| `sitewatch add` | `URL` — page to watch | `--selector TEXT` (required, CSS selector); `--name TEXT` (required); `--min-interval INT` (seconds, default `1800` = 30 min) | Register a page + selector to watch for content changes |
| `sitewatch list` | — | — | Table of all registered watches, including last-checked time |
| `sitewatch remove` | `WATCH_ID` | — | Delete a watch |
| `sitewatch start` | — | `--interval INT` (loop tick, seconds, default `1800`); `--channels TEXT` (comma-separated `notify` channel names, default `desktop`); `--config PATH` (confload YAML/JSON for `notify` webhook credentials) | Poll every due watch on a loop, forever, until Ctrl+C |

Exit code is `1` (with a message on stderr/stdout) for: a duplicate `add`
(same URL+selector already registered), `remove` on a nonexistent ID, or
`start` with zero watches registered.

### Registering a watch

```bash
sitewatch add "https://example.com/product/123" --selector "#price" --name "Widget price"
```

`--selector` is any CSS selector BeautifulSoup's
[`select_one()`](https://www.crummy.com/software/BeautifulSoup/bs4/doc/#css-selectors)
accepts — id (`#price`), class (`.stock-status`), tag, attribute selectors,
descendant/child combinators (`div.product > span.price`), etc. Only the
*first* matching element is watched; if the selector matches nothing, that
check is logged as a warning and skipped (it does not remove the watch or
stop other watches from being checked).

### Managing watches

```bash
sitewatch list             # show all registered watches, including last-checked time
sitewatch remove 2         # remove watch #2
```

### Checking for updates

```bash
sitewatch start                             # loop, checking every 30 min (default)
sitewatch start --channels discord          # fan out via notify's discord channel
sitewatch start --config secrets.yaml       # confload file with notify webhook credentials
```

`start` loops forever (Ctrl+C to stop), waking up every `--interval` seconds
and, each tick, re-checking whichever registered watches are currently
*due* — see "Avoiding excessive polling" below for what that means. Checks
are sequential (no per-watch concurrency); fine for a personal watch list,
not built for hundreds of pages.

For each due watch: fetch `URL` (via `reqretry`, so a timeout/connection
error/5xx gets retried with backoff before being treated as a failure),
extract the first element matching `--selector` with BeautifulSoup, and
SHA256-hash its **text content** (`element.get_text(strip=True)` — not the
raw HTML, so markup-only churn like a changed `data-*` attribute or inline
style doesn't count as a change). That hash is compared against the hash
recorded on the *previous* check:

- **First check ever** for a watch: no previous hash exists, so this just
  records a baseline — it never notifies on its own.
- **Hash unchanged**: nothing happens (the check still updates
  `last_checked_at`, resetting the due-interval clock).
- **Hash changed**: a notification is sent, and the new hash + timestamp
  are recorded.

A fetch error (network failure, non-2xx after retries) or a selector match
failure is logged (`logging.getLogger("sitewatch")`, level `WARNING`) and
that watch is skipped for the cycle; `last_checked_at`/`last_hash` are left
untouched so it will be retried on the next due cycle. It doesn't stop the
rest of the cycle or crash the loop.

### `--config` file format

`--config` is a [`confload`](../confload) YAML (or JSON) file, loaded once
at `start` and passed through as `notify()`'s `config=` for every
notification. Keys are the lowercased env var names for whichever `notify`
channel(s) you pass via `--channels` — mix and match only the ones you
actually use:

```yaml
# secrets.yaml
discord_webhook_url: https://discord.com/api/webhooks/xxxxx/yyyyy
slack_webhook_url: https://hooks.slack.com/services/xxx/yyy/zzz
```

```bash
sitewatch start --channels discord,slack --config secrets.yaml
```

Without `--config`, everything falls back to the matching environment
variable (`DISCORD_WEBHOOK_URL`, `SLACK_WEBHOOK_URL`, etc.) — see
[`notify`'s README](../notify/README.md#channels-and-their-configuration)
for the full list per channel. `desktop` (the default) needs no
credentials at all.

### Running `start` continuously

`sitewatch start` is a foreground loop — it does nothing once you close the
terminal it's running in (or log out), so for it to actually catch content
changes over time it needs to keep running unattended:

- **Simplest**: leave a terminal window open running `sitewatch start`
  (or run it in a background job — e.g. `Start-Process` in PowerShell, or
  `nohup sitewatch start &` in a POSIX shell).
- **Run at Windows logon** (Task Scheduler):
  1. Write a small wrapper batch file, e.g. `sitewatch-start.bat`:
     ```bat
     @echo off
     cd /d C:\path\to\devtools\sitewatch
     sitewatch start --channels discord --config C:\path\to\secrets.yaml >> sitewatch.log 2>&1
     ```
  2. Open Task Scheduler → *Create Task* → Trigger: *At log on*. Action:
     *Start a program*, pointing at the `.bat` file above.
  3. On the *Settings* tab, check *"If the task is already running, do not
     start a new instance"* — the script itself loops forever, so the task
     only needs to be launched once per logon, not repeated.
  4. Check `sitewatch.log` for output/errors (`start` logs fetch/selector
     failures there via the `sitewatch` logger, but keeps going).

### Notification format

A detected change calls [`notify.notify()`](../notify) once, with:

```
[{watch name}] changed: {watch URL}
```

e.g. `[Widget price] changed: https://example.com/product/123`. `channels`
and `config` are passed straight through from `sitewatch start`'s own
`--channels`/`--config` to every `notify()` call; see [`notify`'s
README](../notify/README.md) for the channel list (`slack`, `discord`,
`line`, `desktop`) and their credential env vars/config keys.

### Avoiding excessive polling

Each watch has its own minimum polling interval (`--min-interval`, in
seconds, **default 1800 = 30 minutes**), enforced independently of `start`'s
own loop tick (`--interval`, same default): a watch is only actually
re-fetched once at least `min-interval` seconds have passed since its
`last_checked_at`, however often the loop itself wakes up. This is a floor,
not a target — if the loop's `--interval` is *longer* than a watch's
`min-interval`, that watch simply gets checked once per loop tick (still
never more often than intended, just not necessarily as often as its
`min-interval` alone would allow).

```bash
sitewatch add "https://example.com/rare-restock" --selector ".stock-status" \
    --name "Restock check" --min-interval 300   # check this one every 5 min instead
```

## Data model

SQLite database at `~/.sitewatch/sitewatch.db` (override the directory with
the `SITEWATCH_HOME` env var — mainly used by the test suite to isolate each
test's data). One table:

```sql
CREATE TABLE watches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    selector TEXT NOT NULL,
    name TEXT NOT NULL,
    min_interval_sec INTEGER NOT NULL DEFAULT 1800,
    last_hash TEXT,              -- NULL until the first successful check
    last_checked_at TEXT,        -- ISO 8601 UTC; NULL until the first successful check
    created_at TEXT NOT NULL,    -- ISO 8601 UTC
    UNIQUE (url, selector)
);
```

`UNIQUE (url, selector)` means the same page can be watched multiple times
with *different* selectors (e.g. price and stock status on the same product
page), but not registered twice with the same selector.

## Architecture

| Module | Responsibility |
| --- | --- |
| `sitewatch/db.py` | SQLite schema + CRUD (`watches`), plus `is_due()` (min-interval check) |
| `sitewatch/scraper.py` | Page fetch (via `reqretry`) + CSS-selector extraction and hashing (via `BeautifulSoup`) |
| `sitewatch/poller.py` | One check pass per watch (`check_watch`/`check_all`) and the `start` loop (`run_forever`) |
| `sitewatch/cli.py` | Typer CLI wiring the above into `add`/`list`/`remove`/`start` |
| `sitewatch/paths.py` | `~/.sitewatch/` home directory resolution (`SITEWATCH_HOME` override) |

## Development

```bash
pip install -e ../reqretry -e ../confload -e ../notify
pip install -e ".[dev]"
pytest
```

Tests use [`responses`](https://github.com/getsentry/responses) to mock the
page-fetch HTTP calls (no real network access), and monkeypatch `notify` to
assert on what would have been sent, without touching real notification
channels.
