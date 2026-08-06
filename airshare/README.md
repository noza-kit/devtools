# airshare

An AirDrop-like local web server for sending files between iPhone and PC
over the same Wi-Fi network. `airshare start` launches a small FastAPI
server, prints an ASCII QR code for the PC's LAN URL, and iPhone Safari
just needs to scan it — no app install required. Windows is the primary
target, with a desktop `.bat` shortcut generator for one-click launch.

## Install

```bash
cd airshare
pip install -e ".[dev]"
```

From GitHub (this package lives in the `airshare/` subdirectory of the repo):

```bash
pip install "git+https://github.com/noza-kit/devtools.git#subdirectory=airshare"
```

## Usage

```bash
airshare start
```

This prints an ASCII QR code and the server URL
(`http://<PCのローカルIP>:8000/`). Scan it with iPhone's Camera app or Safari:

- **PC → iPhone**: files placed in `~/Documents/AirShare/send` show up as a
  tappable, downloadable list on the page.
- **iPhone → PC**: tap "ファイルを選ぶ" (or drag & drop on a PC browser) to
  upload photos/PDFs; they're saved to `~/Documents/AirShare/received`.

Stop the server with `Ctrl+C`, or from another terminal:

```bash
airshare stop
```

### `airshare start`

```
airshare start [--port/-p PORT] [--send-dir PATH] [--receive-dir PATH] [--passcode CODE] [--no-browser]
```

- `--port` / `-p` — port to listen on (default: `8000`, or `$AIRSHARE_PORT`).
- `--send-dir` — folder shared PC → iPhone (default: `~/Documents/AirShare/send`, or `$AIRSHARE_SEND_DIR`).
- `--receive-dir` — folder uploads land in, iPhone → PC (default: `~/Documents/AirShare/received`, or `$AIRSHARE_RECEIVE_DIR`).
- `--passcode` — simple passcode required to use the server (default: none, or `$AIRSHARE_PASSCODE`). When set, it's embedded in the QR code URL so scanning it logs you in automatically.
- `--no-browser` — don't open the QR code page in a browser on start.

Refuses to start a second instance while one is already running (checked
via `~/.airshare/run.json` + a live health check).

### `airshare stop`

Stops a running server. Tries a graceful shutdown over local HTTP first
(using a random token written to `~/.airshare/run.json` at start time);
falls back to force-terminating the process by PID if the server didn't
respond.

### `airshare setup-shortcut` (Windows only)

```
airshare setup-shortcut [--port/-p PORT] [--passcode CODE]
```

Writes `AirShare 起動.bat` to the Desktop. Double-clicking it runs
`airshare start` with the given port/passcode and opens the QR code page
in the default browser.

## Watch mode (`airshare watch`)

airshare's companion feature: watches the Inbox (by default, the same
`--receive-dir` folder `airshare start` already delivers iPhone uploads
into) and, for every newly-received file, automatically sorts it into
the right folder, optionally runs a hook command against it, and fires
a clickable desktop notification — so files land where you want them
without manual sorting or manual "did anything new arrive?" checking.

```bash
airshare watch start                  # Ctrl+C to stop
airshare watch status                 # is it running? what's arrived in the last 24h?
airshare watch clean                  # manually run the daily stale-file cleanup
airshare watch clean --force          # skip the confirmation prompt
```

### Config (`~/.airshare/watch.yaml`, or `--config path/to/file.yaml`)

```yaml
inbox_dir: "~/Documents/AirShare/received"   # default: airshare's own receive_dir
debounce_seconds: 3

routing:
  pictures:
    extensions: [".jpg", ".png", ".heic"]
    destination: "~/Pictures/Airshare"
  docs:
    extensions: [".pdf", ".md"]
    destination: "~/Documents/Airshare"

hooks:
  ".pdf": "pdfcraft compress {filepath} --replace"
  ".md": "notesearch sync"

cleanup:
  enabled: true
  expire_days: 7
```

Every key is optional — an unset key falls back to the default shown
above (no config file at all is also fine). A file whose extension
doesn't match any `routing` rule stays in `inbox_dir` untouched, rather
than being dropped or erroring.

### How it works

1. **Detection**: files with a transfer-in-progress suffix
   (`.tmp`/`.part`/`.crdownload`) are ignored entirely — they never
   even enter tracking. Every other file-created/modified/renamed event
   is tracked; once `debounce_seconds` have passed with **no further**
   event for that specific file, it's considered "done writing" and
   included in the next batch. (Windows' file-watching API doesn't
   expose a real close-on-write signal the way Linux's inotify does, so
   this debounce is the practical stand-in for "the final write
   completed.")
2. **Routing**: each settled file moves into the first `routing` rule
   whose `extensions` match its suffix (case-insensitive), or stays put
   if nothing matches. A name collision at the destination is resolved
   as `name (1).ext`, `name (2).ext`, ... (same scheme as `airshare`'s
   own upload handling).
3. **Hooks**: if the (now-routed) file's extension has a `hooks` entry,
   that command runs via the shell (`{filepath}` substituted with the
   file's new path) — e.g. auto-compressing a routed PDF with
   [`pdfcraft`](../pdfcraft), or indexing a routed Markdown note into
   [`notesearch`](../notesearch). A failing or crashing hook is logged
   and does not block routing/notification for this or any other file.
4. **Notification**: one Windows toast per batch (not per file),
   summarizing counts per destination folder (e.g. "3件のファイルを受信
   しました: Pictures 2件, Documents 1件"). Clicking the toast opens the
   destination folder in Explorer. This uses
   [`winotify`](https://github.com/versa-syahptr/winotify) directly
   rather than routing through this repo's own [`notify`](../notify)
   package, since `notify`'s desktop channel (`plyer`-based, for
   cross-platform portability) doesn't expose a click callback the way
   a Windows-specific toast library does.
5. **Cleanup**: once a day (while `watch start` keeps running), any
   file older than `cleanup.expire_days` (by last-access time) in any
   routing destination or the inbox itself is moved to the Recycle Bin
   (not permanently deleted) via
   [`send2trash`](https://github.com/arsenetar/send2trash).
   `airshare watch clean` runs this same check on demand.

`airshare watch status` shows whether a `watch start` process is
currently running (tracked in `~/.airshare/watch_run.json`, the same
pattern `airshare start`/`stop` already use for the main server) and
recent batch activity from `~/.airshare/watch_log.jsonl` (default: last
24 hours, `--hours` to adjust).

## Security

This is meant for a trusted home/office Wi-Fi network, not the open
internet:

- Every request is checked against the client's source IP; anything
  outside loopback / RFC1918 private ranges (`10.*`, `172.16-31.*`,
  `192.168.*`, `127.0.0.1`) gets a `403`. This is defense-in-depth on top
  of your router not port-forwarding the LAN to the internet — it does
  not replace a firewall.
- `--passcode` (or `$AIRSHARE_PASSCODE`) adds a shared-secret check on top,
  since anyone else on the same Wi-Fi can otherwise reach the server.
- The `/qr` page (which reveals the passcode in the clear for display) and
  the shutdown endpoint used by `airshare stop` only accept requests from
  `127.0.0.1` — never from the LAN.
- Uploaded/downloaded filenames are reduced to their basename before
  touching the filesystem, so `../../etc/passwd`-style names can't escape
  the configured send/receive folders.

## Development

```bash
pip install -e "../confload"
pip install -e ".[dev]"
pytest
```

`watch_*` module tests (the `airshare watch` feature) run real
subprocess hook commands, a real `send2trash` call, and a real
`winotify` toast (confirmed to actually work in this development
environment) rather than mocking them — only the debounce timing
(injectable `now_fn`) and the real `watchdog` filesystem observer/
`airshare watch start`'s foreground loop itself are not exercised by
the automated suite (the former is a pure state machine tested
directly instead; the latter needs a live filesystem + Ctrl+C to stop,
same as this repo's other daemon-style tools).
