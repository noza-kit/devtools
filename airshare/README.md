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
pip install -e ".[dev]"
pytest
```
