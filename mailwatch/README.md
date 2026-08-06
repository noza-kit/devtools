# mailwatch

Polls Gmail for messages matching rules defined in a YAML file, and notifies
via Slack/Discord/desktop/etc. through [`notify`](../notify). Deduplicates
via a local SQLite record of processed message IDs, and can optionally save
attachments from matching messages to a folder.

- [Install](#install)
- [Gmail API setup (one-time)](#gmail-api-setup-one-time)
- [Quick start](#quick-start)
- [CLI reference](#cli-reference)
- [Config file reference](#config-file-reference)
- [Specification](#specification)
  - [Architecture](#architecture)
  - [Poll cycle](#poll-cycle)
  - [Rule matching](#rule-matching)
  - [Deduplication](#deduplication)
  - [Notification format](#notification-format)
  - [Attachment saving](#attachment-saving)
  - [Authentication / token lifecycle](#authentication--token-lifecycle)
  - [Error handling](#error-handling)
- [Files on disk](#files-on-disk)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

## Install

```bash
cd mailwatch
pip install -e ../reqretry
pip install -e ../notify
pip install -e ".[dev]"
```

## Gmail API setup (one-time)

1. In the [Google Cloud Console](https://console.cloud.google.com/), create
   (or pick) a project, enable the **Gmail API**, and configure the OAuth
   consent screen as **Testing** with your own Google account added as a
   test user (this is a personal tool, not a published app — "Testing" mode
   avoids Google's app verification review and works indefinitely for
   accounts you add as testers).
2. Create an **OAuth client ID** of type **Desktop app**, and download its
   JSON.
3. Save it as `~/.mailwatch/credentials.json` (or pass `--credentials
   <path>` to `mailwatch auth`/`mailwatch start`).

mailwatch only ever requests the `gmail.readonly` scope — it reads messages
and attachments, and never modifies, labels, or deletes anything in the
mailbox.

**Never commit `credentials.json` or `token.json`** — both are git-ignored
by default (`mailwatch/.gitignore`). `credentials.json` is your OAuth
client's identity; `token.json` is a live credential that can read the
connected mailbox. Keep both out of version control and don't share them.

## Quick start

```bash
# 1. One-time: authenticate (opens a browser for the Google consent screen)
mailwatch auth

# 2. Copy the example config and fill in real addresses/keywords/webhooks
cp rules.example.yaml rules.yaml

# 3. Start polling (Ctrl-C to stop)
mailwatch start --config rules.yaml
```

`mailwatch start` also runs the auth flow automatically on first use if no
token is saved yet, so step 1 is optional — but running it separately lets
you confirm login works before leaving the poller running unattended.

## CLI reference

### `mailwatch auth`

Runs the Gmail OAuth2 consent flow and saves the token. Useful to
authenticate (or re-authenticate) without also starting the polling loop.

| Flag | Default | Meaning |
| --- | --- | --- |
| `--credentials <path>` | `~/.mailwatch/credentials.json` | OAuth client secrets JSON downloaded from Google Cloud Console |
| `--token <path>` | `~/.mailwatch/token.json` | Where to write the resulting OAuth token |
| `--force` | off | Delete any existing token first and force a fresh browser consent flow (e.g. after revoking access, or switching Google accounts) |

### `mailwatch start`

Starts the polling loop. Runs until interrupted (Ctrl-C).

| Flag | Default | Meaning |
| --- | --- | --- |
| `--config, -c <path>` | *(required)* | YAML file defining watch rules |
| `--interval <seconds>` | `poll_interval_seconds` from the config, or `300` | Poll interval; overrides the config value when given |
| `--credentials <path>` | `~/.mailwatch/credentials.json` | OAuth client secrets JSON |
| `--token <path>` | `~/.mailwatch/token.json` | OAuth token storage path |
| `--db <path>` | `~/.mailwatch/seen.db` | SQLite DB of processed message IDs |
| `--verbose, -v` | off | Debug-level logging |

All three paths (`--credentials`/`--token`/`--db`) default under
`~/.mailwatch/`, which is itself overridable via the `MAILWATCH_HOME`
environment variable (e.g. to run multiple independent watchers, each with
its own `MAILWATCH_HOME`).

## Config file reference

Start from [`rules.example.yaml`](rules.example.yaml):

```yaml
poll_interval_seconds: 300

gmail:
  query: "in:inbox newer_than:1d"

attachments:
  enabled: false
  save_dir: "./attachments"

rules:
  - name: boss-urgent
    from: "boss@example.com"
    subject_contains: ["至急", "請求書"]
    channels: ["slack"]
    save_attachments: true
    attachment_dir: "./attachments/boss"

  - name: invoices
    body_contains: ["請求書番号", "お支払い"]
    channels: ["discord", "slack"]

notify:
  slack_webhook_url: "https://hooks.slack.com/services/..."
  discord_webhook_url: "https://discord.com/api/webhooks/..."
```

### Top-level keys

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `poll_interval_seconds` | int | `300` | Seconds between poll cycles; overridden by `--interval` |
| `gmail.query` | string | `"in:inbox newer_than:1d"` | [Gmail search syntax](https://support.google.com/mail/answer/7190) narrowing what each poll cycle fetches |
| `attachments.enabled` | bool | `false` | Default value for a rule's `save_attachments` when the rule doesn't set it |
| `attachments.save_dir` | string | `"./attachments"` | Default value for a rule's `attachment_dir` when the rule doesn't set it |
| `rules` | list | *(required, non-empty)* | The watch rules — see below |
| `notify` | mapping | `{}` | Passed straight through as the `config` argument to [`notify()`](../notify); e.g. `slack_webhook_url`, `discord_webhook_url`, `line_channel_access_token`, `line_to`. Any key can instead come from the matching environment variable (`SLACK_WEBHOOK_URL`, etc.) — see notify's README |

### Rule keys (each entry under `rules:`)

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `name` | string | `rule-<N>` (1-based position) | Identifies the rule in logs, notifications, and the SQLite record. Must be unique across the file |
| `from` | string | *(none)* | Substring, matched case-insensitively against the raw `From` header (e.g. `"boss@example.com"` also matches `"Boss <boss@example.com>"`) |
| `subject_contains` | list of strings | `[]` | Keywords; the condition passes if **any** keyword is a case-insensitive substring of the subject |
| `body_contains` | list of strings | `[]` | Keywords; the condition passes if **any** keyword is a case-insensitive substring of the plain-text body |
| `channels` | list of strings | *(required, non-empty)* | `notify()` channel names to fire on a match: `slack`, `discord`, `line`, `desktop` |
| `save_attachments` | bool | `attachments.enabled` | If true, download this message's attachments when the rule matches |
| `attachment_dir` | string | `attachments.save_dir` | Folder attachments are saved into when this rule matches and has attachments |

Every rule must set at least one of `from` / `subject_contains` /
`body_contains` — a config that loads without an error always has
resolvable matching logic. Config loading (`load_rules_config`) raises
`RuleConfigError` with a specific message for: no `rules` list, a rule
missing `channels`, a rule with no matching conditions, or a duplicate rule
`name`.

## Specification

### Architecture

| Module | Responsibility |
| --- | --- |
| `cli.py` | `typer` entry points: `auth`, `start` |
| `paths.py` | Resolves `~/.mailwatch/` (or `$MAILWATCH_HOME`) and the default file paths under it |
| `auth.py` | OAuth2 consent flow, token load/refresh/persist |
| `gmail_client.py` | Thin Gmail REST API wrapper over `reqretry` (list/get messages, fetch attachment bytes) |
| `message.py` | Turns a raw Gmail API message into a flat `ParsedMessage` (headers, plain-text body, attachment list) |
| `rules.py` | YAML config parsing/validation into `Rule`/`WatchConfig`, and `Rule.matches()` |
| `store.py` | SQLite-backed `SeenStore` for dedup |
| `attachments.py` | Downloads and writes a message's attachments to disk |
| `poller.py` | Ties it together: the poll cycle (`poll_once`) and the run loop (`run_forever`) |

### Poll cycle

Each cycle (`poll_once` in `poller.py`):

1. `GET /messages?q=<gmail.query>` — list up to 50 message IDs matching the
   configured Gmail search query (most recent first; see
   `gmail_client.DEFAULT_MAX_RESULTS`). Pagination continues automatically
   if `gmail.query` is broad enough to return more than one page, up to
   that cap.
2. Filter out IDs already present in the SQLite `seen_messages` table.
3. For each remaining (new) ID:
   1. `GET /messages/{id}?format=full` and parse it into a `ParsedMessage`.
   2. Evaluate every configured rule's `matches()` against it.
   3. For each matching rule (a message can match more than one): call
      `notify(text, channels=rule.channels, config=notify_config)`, then, if
      `rule.save_attachments` is true and the message has attachments,
      download and save them to `rule.attachment_dir`.
   4. Record the message ID as seen — **whether or not any rule matched** —
      along with the names of the rules that did match.
4. Sleep for `interval_seconds`, then repeat.

Because the narrowing `gmail.query` window (default: messages from the last
day) and the SQLite seen-table are independent, a message keeps being
listed by step 1 on every poll within that window, but step 2 skips it
immediately once it's been recorded — so it's fetched and evaluated exactly
once regardless of how many polls happen inside that window.

### Rule matching

`Rule.matches(message)` (`rules.py`):

- Each of `from` / `subject_contains` / `body_contains` set on the rule is
  a separate condition; **all** conditions set on the rule must pass (AND).
  A condition left unset (empty/absent) is skipped entirely — it does not
  count as a failure.
- Within `subject_contains` / `body_contains`, the condition passes if
  **any** one keyword matches (OR).
- All string comparisons are plain, case-insensitive substring checks
  (`in`, not regex or word-boundary matching) — a keyword like `"至急"`
  matches anywhere it appears in the subject/body text.
- `from` matches against the full raw header value (e.g.
  `"Boss <boss@example.com>"`), not a parsed address, so it also matches on
  a display name substring if you write one.
- A message can match zero, one, or several rules independently; each
  matching rule fires its own `notify()` call to its own `channels`.

### Deduplication

`SeenStore` (`store.py`) is a SQLite table:

```sql
CREATE TABLE seen_messages (
    message_id     TEXT PRIMARY KEY,
    processed_at   TEXT NOT NULL,   -- UTC, sqlite datetime('now')
    matched_rules  TEXT NOT NULL    -- comma-joined rule names, "" if none matched
)
```

A message ID is inserted (`INSERT OR IGNORE`) once it has been fetched and
evaluated in a poll cycle, regardless of whether any rule matched. This
means: a message that matched nothing is never re-evaluated on a later
poll either, so tightening or adding a rule later does not retroactively
re-scan messages already seen under the old rule set — only newly-arriving
messages are affected. The DB persists across restarts (default
`~/.mailwatch/seen.db`), and is git-ignored.

### Notification format

The text passed to `notify()` for a match (`_format_notification` in
`poller.py`):

```
[mailwatch] ルール「<rule.name>」に一致するメールを検知しました
差出人: <From header>
件名: <Subject header>
受信日時: <Date header, or the message's internalDate as UTC ISO-8601 if the header is missing>
```

One `notify()` call is made per matching rule (not per message), so a
message matching two rules produces two separate notifications, each
naming its own rule and each sent to that rule's own `channels`. A channel
delivery failure (e.g. webhook down) is logged as a `WARNING` and does not
stop other channels or other rules from being tried — see `notify`'s own
retry behavior in [`notify/README.md`](../notify/README.md).

### Attachment saving

When a matching rule has `save_attachments: true` and the message has one
or more attachments (`save_attachments` in `attachments.py`):

- `rule.attachment_dir` is created if it doesn't exist.
- Each attachment is fetched via `GET
  /messages/{id}/attachments/{attachmentId}` and base64url-decoded.
- Saved as `<message_id>_<sanitized_filename>` — the message ID prefix
  guarantees no collision between attachments of the same name from
  different emails. Filename characters unsafe on Windows
  (`\ / : * ? " < > |`) are replaced with `_`; an empty/all-unsafe filename
  falls back to `attachment`.
- A download failure for one message's attachments is logged as an
  `ERROR` and does not affect the notification already sent, other
  matching rules, or later messages.

### Authentication / token lifecycle

- `mailwatch auth` / the first `mailwatch start`: if `token.json` doesn't
  exist or has no usable/refreshable credentials, runs
  `InstalledAppFlow.run_local_server()` (opens the system browser), then
  writes the resulting token — including its refresh token — to
  `token.json`.
- Every subsequent `mailwatch start`: loads `token.json`; if the access
  token is expired, refreshes it via the stored refresh token
  (`google.auth.transport.requests.Request`) with no browser involved, and
  rewrites `token.json` with the refreshed token.
- Inside the poll loop, a refresh is attempted once per cycle before
  polling (`refresh_if_needed`); if it fails (e.g. the refresh token was
  revoked), the cycle is skipped, an error is logged, and the loop retries
  on the next interval rather than exiting — recovery requires running
  `mailwatch auth --force` in a separate invocation.
- On POSIX, `token.json` is written with `0600` permissions
  (owner read/write only); this has no effect on Windows, so keep
  `~/.mailwatch/` (or `$MAILWATCH_HOME`) out of any shared/synced location
  there.

### Error handling

| Failure | Behavior |
| --- | --- |
| `gmail.query` list call fails (network, 4xx/5xx after `reqretry`'s retries) | Logged as `ERROR`; that poll cycle processes 0 messages, next cycle retries |
| Fetching one message's full body fails | Logged as `ERROR`; that message is skipped (not marked seen, so it's retried next cycle) and the cycle continues with the rest |
| `notify()` channel delivery fails | Logged as `WARNING`; other channels/rules for the same message still run |
| Attachment download fails | Logged as `ERROR`; does not block the notification or other rules |
| Token refresh fails | Logged as `ERROR`; that poll cycle is skipped entirely, retried next interval |
| Any other unexpected exception during a poll cycle | Caught and logged with a traceback (`logger.exception`) at the `run_forever` level; the loop keeps running rather than crashing the process |

`reqretry` (used for both the Gmail REST calls and `notify`'s webhook
calls) separately retries timeouts, connection errors, and 5xx responses
with exponential backoff before any of the above "failed" paths are
reached — see [`reqretry/README.md`](../reqretry/README.md).

## Files on disk

Everything defaults under `~/.mailwatch/` (override with the
`MAILWATCH_HOME` environment variable):

| File | Written by | Purpose |
| --- | --- | --- |
| `credentials.json` | you (downloaded from Google Cloud Console) | OAuth client secrets |
| `token.json` | `mailwatch auth` / `mailwatch start` | OAuth access + refresh token (0600 on POSIX) |
| `seen.db` | `mailwatch start` | SQLite dedup record (`seen_messages` table) |

Plus, per rule, whatever `attachment_dir` you configured (default
`./attachments`, relative to the current working directory `mailwatch
start` is run from).

## Troubleshooting

- **`OAuth client credentials not found at ...`** — `credentials.json`
  isn't at the expected path; pass `--credentials <path>` or move the file
  there.
- **`No valid Gmail token at ...`** during `mailwatch start`'s poll loop
  (not the first run) — the refresh token was rejected (commonly: access
  was revoked in your Google Account's connected-apps settings, or the
  OAuth consent screen's Testing-mode grant expired). Run `mailwatch auth
  --force`.
- **No notifications despite matching mail** — check `mailwatch start
  --verbose` output; a channel failure logs a `WARNING` with the reason
  (e.g. missing `SLACK_WEBHOOK_URL`). Also confirm the rule's `channels`
  list and the corresponding `notify.*` key/env var are both set.
- **A message I expect to match doesn't** — confirm it falls within
  `gmail.query`'s window (default `newer_than:1d`); a message can only be
  evaluated once, so if the window already passed it before you added or
  fixed the rule, mailwatch will not retroactively re-scan it unless you
  remove its row from `seen.db` or delete `seen.db` entirely (this
  re-evaluates everything currently in `gmail.query`'s window, including
  messages already notified before).

## Development

```bash
pip install -e ../reqretry
pip install -e ../notify
pip install -e ".[dev]"
pytest
```

Tests cover rule matching/config validation, message parsing, the Gmail
REST client (via `responses`), attachment saving, and the SQLite dedup
store — none touch the real Gmail API or send real notifications.
