# snapclip

A Windows screenshot + clipboard extension. Two things it deliberately
does *not* reimplement: plain "copy to clipboard as text" (already
`Win+V`) and a general screenshot tool (already `Win+Shift+S`) — this
tool exists for the gaps around those: a capture queue that survives
several screenshots in a row, auto-generated Markdown/LaTeX figure
syntax instead of raw image data on the clipboard, scroll-stitching for
tall content, full-page web capture, and a searchable clipboard history.

- [Install](#install)
- [Daemon mode (hotkeys)](#daemon-mode-hotkeys)
- [The shared paste queue](#the-shared-paste-queue)
- [Scroll capture](#scroll-capture)
- [`snapclip web`](#snapclip-web)
- [`snapclip history`](#snapclip-history)
- [`snapclip config`](#snapclip-config)
- [Known limitations](#known-limitations)
- [Development](#development)

## Install

Windows only.

```bash
cd snapclip
pip install -e "../confload"   # local dependency, not on PyPI
pip install -e ".[dev]"
```

`snapclip web` needs the optional `web` extra (Playwright) plus a
one-time browser download:

```bash
pip install -e ".[web]"
playwright install chromium
```

> **Admin rights**: the `keyboard` package (global hotkeys) sometimes
> needs an elevated (Run as Administrator) terminal to hook keys
> system-wide on Windows, depending on what else is running with
> elevated privileges on your machine. If `snapclip daemon start`
> reports permission errors, try an elevated terminal.

## Daemon mode (hotkeys)

```bash
snapclip daemon start
```

Runs in the foreground (Ctrl+C to stop) and registers three global
hotkeys:

| Hotkey | Action |
| --- | --- |
| `Alt+Shift+S` | Stack screenshot: capture the full screen, save it under the configured image directory, push its Markdown/LaTeX markup onto the paste queue |
| `Alt+Shift+V` | FIFO paste: pop the oldest item off the paste queue, set it as the clipboard content, and send `Ctrl+V` |
| `Alt+Shift+C` (**held**) | Scroll capture — see [below](#scroll-capture) |

```bash
snapclip daemon start --mode latex --img-dir ./tex_figures
snapclip daemon start --paste-mode all      # Alt+Shift+V drains and pastes everything at once, joined by newlines
snapclip daemon start --snap-key "ctrl+alt+s" --paste-key "ctrl+alt+v" --scroll-key "ctrl+alt+c"
```

`--mode`/`--img-dir` override the saved config (see
[`snapclip config`](#snapclip-config)) for this run only. `--paste-mode`
defaults to `one` (pop one item per press — the primary FIFO behavior);
`all` instead pops and pastes everything currently queued in one go,
per the spec's alternate "一気にペースト" mode.

## The shared paste queue

Snap's stack-capture and Clip's FIFO paste are, deliberately, **the same
queue** — not two separate systems. Every `Alt+Shift+S` capture pushes
its rendered Markdown/LaTeX snippet onto the queue (not the raw image —
see [Auto-Markup](#daemon-mode-hotkeys) above); every externally-copied
piece of text or image (detected by polling the OS clipboard's sequence
number, since Windows doesn't push clipboard-change notifications to an
ordinary Python process without a hidden-window message hook) is pushed
onto that same queue. So:

```
Ctrl+C "山田太郎"        -> queue: ["山田太郎"]
Alt+Shift+S (screenshot) -> queue: ["山田太郎", "![...](images/....png)"]
Ctrl+C "090-1234-5678"   -> queue: ["山田太郎", "![...](...)", "090-1234-5678"]

Alt+Shift+V -> pastes "山田太郎", queue: ["![...](...)", "090-1234-5678"]
Alt+Shift+V -> pastes the screenshot markup, queue: ["090-1234-5678"]
Alt+Shift+V -> pastes "090-1234-5678", queue: []
```

This is implemented as `snapclip.queue.PasteQueue`, a plain FIFO
(`snapclip.clipboard.ClipboardWatcher` pushes external copies onto it;
`take_stack_screenshot()` pushes captures onto it; both `daemon.py`'s
`on_snap`/`poll_clipboard` and `on_paste` just call into it).

## Scroll capture

```
hold Alt+Shift+C
  -> drag out a rectangle with the mouse (left-button down, move, up)
  -> scroll the mouse wheel inside that region to capture more frames
release Alt+Shift+C
  -> frames are stitched top-to-bottom and saved as one tall image
```

Each captured frame is compared against the previous one via OpenCV
template matching (`snapclip.stitch.find_vertical_overlap`): the bottom
strip of the previous frame is located inside the new frame, and only
the new, non-duplicate rows are appended. This is a custom vertical-
scroll-specific stitcher, not a generic panorama algorithm (`cv2.Stitcher`)
— generic panorama stitching is built for photos with 2D perspective
shift, and is both overkill and less reliable for straight-down UI
scrolling than a 1D vertical-offset search. Frame capture is debounced
(default: at most one frame per 150ms) so a fast, physical scroll wheel
doesn't flood the queue.

If no confident overlap is found between two frames (e.g. the content
didn't actually scroll, or scrolled past what template matching can
recognize), the two frames are just concatenated with no rows dropped —
a duplicated sliver is a much smaller problem than silently losing
content.

The whole press/drag/scroll/release flow is a small state machine
(`snapclip.scrollcapture.ScrollCaptureSession`) with **no OS dependency
of its own** — `daemon.py` wires real global hotkey/mouse events to its
`start()`/`on_mouse_down()`/`on_mouse_up()`/`on_scroll()`/`finish()`
methods, but the state machine itself is exercised directly and fully in
tests.

## `snapclip web`

```bash
snapclip web "https://github.com/example/repo" -o fullpage.png
snapclip web "https://example.com" -o page.png --viewport-width 1920
```

Full-page (not just-viewport) screenshot of a URL via headless Chromium
(Playwright). Needs `pip install -e ".[web]"` + a one-time `playwright
install chromium` — see [Install](#install).

## `snapclip history`

```bash
snapclip history
snapclip history --limit 500
```

Every clipboard entry that has passed through the shared paste queue
(both externally-copied text/images and snapclip's own screenshot
captures) is also durably recorded to SQLite
(`~/.snapclip/history.db`; images alongside it under
`~/.snapclip/history_images/`) as it happens, independent of the queue
being drained by paste. `snapclip history` opens an fzf-style
incremental-search TUI over that log: type to filter (substring,
case-insensitive), ↑/↓ to move, Enter to re-set the highlighted entry
as the current clipboard content, Esc to quit without selecting.

## `snapclip config`

```bash
snapclip config --show
snapclip config --mode latex --img-dir ./tex_figures
```

Reads/writes `~/.snapclip/config.yaml` (confload-loaded YAML). Only
`mode` (`markdown`/`latex`) and `img_dir` are configurable; hotkeys are
per-invocation flags on `daemon start` rather than saved config, since
changing them is rare and the flags are easy to alias/script around.

## Known limitations

- **No automated verification of real hotkey firing.** In this
  development environment, `keyboard.add_hotkey()` + `keyboard.send()`
  (simulating the same keypress) does not reliably cross-trigger the
  registered callback — this appears to be a sandboxed/headless-session
  limitation of the `keyboard` package's OS hook, not a snapclip bug
  (see `tests/test_daemon.py`'s
  `test_register_hooks_with_real_keyboard_and_mouse_modules_does_not_crash`,
  which *does* confirm hook registration/teardown succeeds for real).
  Actually pressing the hotkeys on a real desktop session needs manual
  verification.
- **No tray icon / GUI status indicator** — out of scope for this
  round per project scope decisions; `daemon start` is a foreground
  terminal process (Ctrl+C to stop).
- **Clipboard history stores everything in plaintext** (SQLite, no
  encryption, no size/retention cap) — by design for this round; be
  aware that copying a password or token will land in
  `~/.snapclip/history.db` like anything else.
- **Scroll-capture stitching assumes pure vertical scrolling** — no
  horizontal shift/zoom compensation. It also assumes distinguishable
  content between frames; stitching a mostly-blank or highly repetitive
  region (e.g. a solid-color background) can under- or over-trim overlap
  since there's nothing distinctive for template matching to lock onto.

## Development

```bash
pip install -e "../confload"
pip install -e ".[dev]"
pytest
```

Real vs. mocked/injected in tests:

- **Real**: Markdown/LaTeX rendering, the paste queue, config load/save,
  the scroll-capture state machine, SQLite history, and — confirmed to
  actually work in this development environment — real Windows
  clipboard text/image read-write via `pywin32`
  (`tests/test_clipboard.py`'s `test_win32_backend_*` tests touch the
  real OS clipboard) and real `keyboard`/`mouse` hook
  registration/teardown (`test_register_hooks_with_real_keyboard_and_mouse_modules_does_not_crash`).
- **Injected fakes**: `ScreenCapture` (`FakeScreenCapture` in
  `tests/conftest.py`, no real screen grab) and `ClipboardBackend`
  (`FakeClipboardBackend`) for the watcher/queue/daemon logic tests,
  so those don't depend on machine state or a real display.
- **Not automated** (see [Known limitations](#known-limitations)):
  actually pressing a hotkey and observing the daemon react, and the
  interactive `history` TUI's keyboard-driven loop itself
  (`snapclip.tui.run_history_tui`) — its filtering logic
  (`snapclip.history.filter_entries`) is unit tested directly instead.
