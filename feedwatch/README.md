# feedwatch

Watch RSS/Atom feeds (YouTube channels, blogs, etc.) and Twitch channels for
new items, and send a [`notify`](../notify) notification when something new
shows up. Already-notified items are tracked in SQLite so nothing gets
announced twice. Companion to [`sitewatch`](../sitewatch), which covers
sites that don't offer RSS at all (arbitrary page content, not just
new-item feeds).

## Install

```bash
cd feedwatch
pip install -e ../reqretry -e ../confload -e ../notify   # local deps, not on PyPI
pip install -e ".[dev]"
```

From GitHub (this package lives in the `feedwatch/` subdirectory of the repo):

```bash
pip install "git+https://github.com/noza-kit/devtools.git#subdirectory=feedwatch"
```

## Quick start

```bash
feedwatch add "https://www.youtube.com/feeds/videos.xml?channel_id=UCxxxxxxxxxxxxxxxxxxxxxx" \
    --name "My Favorite Channel" --tags youtube
feedwatch add-twitch some_streamer --name "Some Streamer" --tags twitch
feedwatch list
feedwatch start                # Ctrl+C to stop
```

## Command reference

| Command | Arguments | Options | Description |
| --- | --- | --- | --- |
| `feedwatch add` | `URL` — RSS/Atom feed URL, or a bare YouTube channel ID (`UC...`, auto-expanded) | `--name TEXT` (required); `--tags TEXT` (comma-separated, default empty) | Register an RSS/Atom feed watch |
| `feedwatch add-twitch` | `CHANNEL_LOGIN` — the name in `twitch.tv/<login>` | `--name TEXT` (required); `--tags TEXT` (comma-separated, default empty) | Register a Twitch channel watch |
| `feedwatch list` | — | — | Table of all registered watches (RSS and Twitch) |
| `feedwatch remove` | `WATCH_ID` | — | Delete a watch and its notification history |
| `feedwatch start` | — | `--interval INT` (seconds, default `600` = 10 min); `--channels TEXT` (comma-separated `notify` channel names, default `desktop`); `--config PATH` (confload YAML/JSON for `notify` webhook / Twitch credentials) | Poll every registered watch on a loop, forever, until Ctrl+C |

Exit code is `1` (with a message on stderr/stdout) for: a duplicate `add`/`add-twitch` (same kind+source already registered), `remove` on a nonexistent ID, or `start` with zero watches registered.

### RSS/Atom feeds (YouTube channels, etc.)

```bash
feedwatch add "https://www.youtube.com/feeds/videos.xml?channel_id=UCxxxxxxxxxxxxxxxxxxxxxx" \
    --name "My Favorite Channel" --tags youtube
```

A bare YouTube channel ID also works and is expanded to the feed URL above
automatically (matched by the pattern `UC` + 22 word/hyphen characters):

```bash
feedwatch add UCxxxxxxxxxxxxxxxxxxxxxx --name "My Favorite Channel" --tags youtube
```

Any standard RSS/Atom feed URL works the same way (blogs, podcasts, etc.) —
YouTube's feed format is just a regular Atom feed, parsed with
[`feedparser`](https://feedparser.readthedocs.io/). Each entry's feed `id`
(falling back to `guid`, then `link`, in that order) is used as its unique
identifier for dedup.

### Twitch channels

Twitch doesn't provide RSS, so live-stream detection is a separate code path
(`feedwatch/twitch.py`) built directly on the [Twitch Helix
API](https://dev.twitch.tv/docs/api/reference/), not feed parsing:

```bash
feedwatch add-twitch some_streamer --name "Some Streamer" --tags twitch
```

This requires a Twitch application (Client ID + Client Secret):

1. Register an app at the [Twitch Developer Console](https://dev.twitch.tv/console/apps)
   (requires a Twitch account with two-factor authentication enabled).
2. Set the credentials as environment variables, or in a
   [`confload`](../confload) config passed to `feedwatch start --config`:

   | Env var | Config key |
   | --- | --- |
   | `TWITCH_CLIENT_ID` | `twitch_client_id` |
   | `TWITCH_CLIENT_SECRET` | `twitch_client_secret` |

feedwatch uses the [client-credentials (app access token) flow](https://dev.twitch.tv/docs/authentication/getting-tokens-oauth/#client-credentials-grant-flow) —
no user login/OAuth redirect needed, just the app's own credentials. The app
token is fetched once (`POST https://id.twitch.tv/oauth2/token`) and reused
across checks; a `401` from the Streams endpoint triggers one automatic
token refresh + retry (handles an expired/revoked token mid-run). If Twitch
credentials aren't configured, Twitch watches are skipped (with a logged
warning) each cycle and RSS watches still run normally — `feedwatch start`
doesn't require Twitch credentials unless you actually have a Twitch watch
registered.

Each channel's live status is checked via `GET
https://api.twitch.tv/helix/streams?user_login=<login>`. A stream gets a new
Twitch-assigned stream ID every time the channel goes live, so "not-yet-seen
stream ID" is used as the "just started streaming" signal — this also means
going offline and coming back live again is correctly treated as a new
broadcast (new stream ID) and notifies again, and a channel that's merely
still live from before doesn't re-notify every cycle.

### Managing watches

```bash
feedwatch list             # show all registered watches (RSS and Twitch)
feedwatch remove 3         # remove watch #3 (also deletes its notification history)
```

### Checking for updates

```bash
feedwatch start                              # poll every 10 minutes (default), desktop notifications
feedwatch start --interval 300                # check every 5 minutes instead
feedwatch start --channels discord,line       # fan out via notify's discord/line channels
feedwatch start --config secrets.yaml         # confload file with notify webhook / Twitch credentials
```

`start` loops forever (Ctrl+C to stop), checking every registered watch each
cycle, in registration order, with no per-watch concurrency (checks are
sequential — fine for a personal watch list, not built for hundreds of
feeds). A feed fetch failure or Twitch API error for one watch is logged
(`logging.getLogger("feedwatch")`, level `WARNING`) and that watch is
skipped for the cycle; it doesn't stop the rest of the cycle or crash the
loop.

### `--config` file format

`--config` is a [`confload`](../confload) YAML (or JSON) file, loaded once
at `start` and passed through as `notify()`'s `config=` for every
notification (Twitch credentials are also read from it, since
`load_credentials()` checks `config` before env vars). Keys are the
lowercased env var names — mix and match only the channels/services you
actually use:

```yaml
# secrets.yaml
discord_webhook_url: https://discord.com/api/webhooks/xxxxx/yyyyy
line_channel_access_token: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
line_to: Uxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
twitch_client_id: your_twitch_client_id
twitch_client_secret: your_twitch_client_secret
```

```bash
feedwatch start --channels discord,line --config secrets.yaml
```

Without `--config`, everything falls back to the matching environment
variable (`DISCORD_WEBHOOK_URL`, `TWITCH_CLIENT_ID`, etc.) — see the
[Twitch channels](#twitch-channels) section above and [`notify`'s
README](../notify/README.md#channels-and-their-configuration) for the full
list per channel.

### Running `start` continuously

`feedwatch start` is a foreground loop — it does nothing once you close the
terminal it's running in (or log out), so for it to actually catch new
uploads/streams over time it needs to keep running unattended:

- **Simplest**: leave a terminal window open running `feedwatch start`
  (or run it in a background job — e.g. `Start-Process` in PowerShell, or
  `nohup feedwatch start &` in a POSIX shell).
- **Run at Windows logon** (Task Scheduler):
  1. Write a small wrapper batch file, e.g. `feedwatch-start.bat`:
     ```bat
     @echo off
     cd /d C:\path\to\devtools\feedwatch
     feedwatch start --channels discord --config C:\path\to\secrets.yaml >> feedwatch.log 2>&1
     ```
  2. Open Task Scheduler → *Create Task* → Trigger: *At log on*. Action:
     *Start a program*, pointing at the `.bat` file above.
  3. On the *Settings* tab, check *"If the task is already running, do not
     start a new instance"* — the script itself loops forever, so the task
     only needs to be launched once per logon, not repeated.
  4. Check `feedwatch.log` for output/errors (`start` logs feed/Twitch
     fetch failures there via the `feedwatch` logger, but keeps going).

### Notification format

Each new item calls [`notify.notify()`](../notify) once, with:

| Source | Message | Example |
| --- | --- | --- |
| RSS/Atom | `[{watch name}] {entry title}\n{entry link}` | `[My Favorite Channel] New upload title\nhttps://www.youtube.com/watch?v=...` |
| Twitch | `[{watch name}] LIVE: {stream title}\n{stream URL}` | `[Some Streamer] LIVE: Ranked grind\nhttps://www.twitch.tv/some_streamer` |

`channels` and `config` are passed straight through from `feedwatch start`'s
own `--channels`/`--config` to every `notify()` call; see
[`notify`'s README](../notify/README.md) for the channel list (`slack`,
`discord`, `line`, `desktop`) and their credential env vars/config keys.

## Data model

SQLite database at `~/.feedwatch/feedwatch.db` (override the directory with
the `FEEDWATCH_HOME` env var — mainly used by the test suite to isolate each
test's data). Two tables:

```sql
CREATE TABLE watches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL CHECK (kind IN ('rss', 'twitch')),
    source TEXT NOT NULL,       -- RSS/Atom feed URL, or Twitch user_login
    name TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',   -- comma-separated
    created_at TEXT NOT NULL,        -- ISO 8601 UTC
    UNIQUE (kind, source)
);

CREATE TABLE seen_items (
    watch_id INTEGER NOT NULL REFERENCES watches(id) ON DELETE CASCADE,
    item_id TEXT NOT NULL,      -- RSS: entry id/guid/link; Twitch: stream id (new per broadcast)
    notified_at TEXT NOT NULL,  -- ISO 8601 UTC
    PRIMARY KEY (watch_id, item_id)
);
```

RSS and Twitch watches share one `seen_items` table — dedup only needs
`item_id` to be unique per watch, regardless of source kind. `UNIQUE (kind,
source)` means the same URL/login can only be registered once per kind (but,
in principle, the same string could exist as both an `rss` and a `twitch`
row without conflict — not a case that comes up in practice). Deleting a
watch (`feedwatch remove`) cascades to delete its `seen_items` rows too.

## Architecture

| Module | Responsibility |
| --- | --- |
| `feedwatch/db.py` | SQLite schema + CRUD (`watches`, `seen_items`) |
| `feedwatch/feeds.py` | RSS/Atom fetch (via `reqretry`) + parse (via `feedparser`), YouTube channel-ID expansion |
| `feedwatch/twitch.py` | Twitch Helix client: app token (client-credentials flow) + Get Streams |
| `feedwatch/poller.py` | One check pass per watch (`check_rss_watch`/`check_twitch_watch`/`check_all`) and the `start` loop (`run_forever`) |
| `feedwatch/cli.py` | Typer CLI wiring the above into `add`/`add-twitch`/`list`/`remove`/`start` |
| `feedwatch/paths.py` | `~/.feedwatch/` home directory resolution (`FEEDWATCH_HOME` override) |

## Data storage

Watches and already-notified items are kept in SQLite at
`~/.feedwatch/feedwatch.db` (override the directory with `FEEDWATCH_HOME`,
mainly useful for tests). Removing a watch (`feedwatch remove`) also deletes
its notification history.

## Development

```bash
pip install -e ../reqretry -e ../confload -e ../notify
pip install -e ".[dev]"
pytest
```

Tests use [`responses`](https://github.com/getsentry/responses) to mock the
feed/Twitch HTTP calls (no real network access), and monkeypatch `notify` to
assert on what would have been sent, without touching real notification
channels.
