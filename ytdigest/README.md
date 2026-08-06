# ytdigest

Daily digest of new YouTube uploads and Twitch activity (live streams + their
VODs once the stream ends), posted to Discord. Runs entirely from GitHub
Actions on a daily cron — no server to keep running. State (which items have
been seen, notified, dismissed, or archived) lives in a SQLite file that's
committed back to the repo after each run.

## How it works

Each run (`ytdigest run`) does, in order:

1. Reads any replies posted since the last run in the **new-content channel**
   and parses `delete 1,3`-style commands against the numbered list from the
   last notification, marking the referenced items `dismissed`.
2. For any Twitch channel currently tracked as "live" (see below), checks
   whether it has gone offline; if so, fetches the resulting VOD from the
   Twitch API and adds it as a new pending item, archiving the original
   "live" item.
3. Fetches new YouTube uploads (via each channel's RSS feed) and newly
   started Twitch live streams, adding them to the database as `pending`.
4. Posts a numbered list of everything newly added this run to the
   **new-content channel**.
5. Sweeps `pending` items that were notified more than 3 days ago and never
   dismissed, moves them to `archived`, and posts them to the **archive
   channel**.

A Twitch channel going live is tracked in `live_tracking` for as long as it
stays live and undismissed — that's how step 2 knows when to look for the
VOD. Dismissing a live item (via `delete`) stops tracking it, so no VOD gets
posted for a stream you said you weren't interested in.

## Setup

### 1. `channels.yaml`

Commit your watch list to `channels.yaml` (see the checked-in example):

```yaml
youtube:
  - channel_id: "UCxxxxxxxxxxxxxxxxxxxxxx"  # the UC... id, not the @handle
    name: "Some Channel"

twitch:
  - login: "somestreamer"  # the twitch.tv/<login> username, not the display name
    name: "Some Streamer"
```

### 2. Discord webhooks (posting)

Create two webhooks (Channel Settings → Integrations → Webhooks → New
Webhook), one in each channel:

- **new-content channel** → `DISCORD_WEBHOOK_NEW`
- **archive channel** → `DISCORD_WEBHOOK_ARCHIVE`

### 3. Discord bot (reading replies)

Webhooks can only post, not read message history, so parsing `delete 1,3`
replies needs an actual bot:

1. Create an application at the [Discord Developer
   Portal](https://discord.com/developers/applications) → **Bot** tab → Add
   Bot.
2. Under **Privileged Gateway Intents**, enable **Message Content Intent**
   (required to read the text of a reply, not just that one exists).
3. Copy the bot token → `DISCORD_BOT_TOKEN`.
4. Under **OAuth2 → URL Generator**, scope `bot`, permissions **View
   Channel** + **Read Message History**, then use the generated URL to
   invite the bot to your server. It only needs those permissions in the
   new-content channel.
5. Enable Developer Mode in Discord (User Settings → Advanced), right-click
   the new-content channel → **Copy Channel ID** → `DISCORD_NEW_CHANNEL_ID`.

### 4. Twitch API (Client Credentials)

1. Register an app at the [Twitch Developer
   Console](https://dev.twitch.tv/console/apps) (any redirect URL works,
   e.g. `http://localhost`; category "Application Integration").
2. Copy the **Client ID** → `TWITCH_CLIENT_ID`.
3. Generate a **Client Secret** → `TWITCH_CLIENT_SECRET`.

This app never needs a user to log in — `ytdigest` authenticates with the
[Client Credentials
flow](https://dev.twitch.tv/docs/authentication/getting-tokens-oauth/#client-credentials-grant-flow),
which only requires these two values and grants an app access token good for
public data (live status, videos) with no per-user scope.

### 5. GitHub Actions secrets

In the repo's **Settings → Secrets and variables → Actions**, add:

| Secret | Value |
|---|---|
| `DISCORD_WEBHOOK_NEW` | webhook URL for the new-content channel |
| `DISCORD_WEBHOOK_ARCHIVE` | webhook URL for the archive channel |
| `DISCORD_BOT_TOKEN` | bot token from step 3 |
| `DISCORD_NEW_CHANNEL_ID` | new-content channel's numeric id |
| `TWITCH_CLIENT_ID` | Twitch app client id |
| `TWITCH_CLIENT_SECRET` | Twitch app client secret |

The workflow at [`.github/workflows/ytdigest.yml`](../.github/workflows/ytdigest.yml)
runs daily, installs `ytdigest` (and its in-repo `reqretry`/`confload`
dependencies), runs the batch, and commits `ytdigest/data/state.db` back to
the repo if it changed.

## Local usage

```bash
pip install -e ./reqretry -e ./confload -e .

export DISCORD_WEBHOOK_NEW=...
export DISCORD_WEBHOOK_ARCHIVE=...
export DISCORD_BOT_TOKEN=...
export DISCORD_NEW_CHANNEL_ID=...
export TWITCH_CLIENT_ID=...
export TWITCH_CLIENT_SECRET=...

ytdigest run --channels channels.yaml --db data/state.db
```

## Database

SQLite, committed to the repo at `data/state.db` so state survives between
GitHub Actions runs:

- **items** — every video/live-stream/VOD ever seen, its `status`
  (`pending` / `archived` / `dismissed`), and (once notified) which
  Discord message + list number it was posted under.
- **live_tracking** — Twitch channels currently live and undismissed;
  drives the "did this stream end yet?" check.
- **meta** — small key/value store, currently just the Discord message-id
  pagination cursor for reply fetching.

The 3-day "notified but not dismissed → archive" window is the
`STALE_AFTER_DAYS` constant in `src/ytdigest/batch.py`.
