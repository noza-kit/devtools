# devtools — 個人開発ツール集

日常の「ちょっと面倒」を解消するために作った、Python 製の小さなツール・ライブラリ集です。
1 ディレクトリ = 1 プロジェクトで、それぞれ独立してインストール・テストできます。
共通ライブラリ（`confload` / `reqretry` / `notify`）を土台に、ツール同士を組み合わせて使えるように設計しています。

A collection of small, independent Python tools I built to automate everyday tasks —
one subdirectory per project, each with its own `pyproject.toml`, tests and README.

- **26 プロジェクト / ~37k 行の Python / 1,400 件以上の pytest テスト**
- Python 3.10+ / Typer CLI / SQLite / GitHub Actions

## 注目プロジェクト / Highlights

| プロジェクト | 内容 | 主な技術 |
| --- | --- | --- |
| [gazemouse](gazemouse/) | Web カメラだけで視線カーソル移動・手のジェスチャーでクリック・首の傾きでスクロールするハンズフリー操作 | MediaPipe, OpenCV, EMA 平滑化 |
| [claude-bridge](claude-bridge/) | Discord から Claude Code をリモート操作する常駐 Bot（許可リスト・危険コマンド確認・タイムアウト・実行履歴付き） | discord.py, subprocess, SQLite |
| [notesearch](notesearch/) | ローカルのノートをベクトル検索 + BM25 のハイブリッドで検索し、RAG 用プロンプト生成や LLM 質問まで行う | SentenceTransformers, ChromaDB, rank-bm25 |
| [airshare](airshare/) | iPhone ↔ PC を同一 Wi-Fi 上で AirDrop のようにファイル共有する Web サーバーと、受信フォルダの自動整理デーモン | FastAPI, watchdog, QR コード |
| [ytdigest](ytdigest/) | YouTube / Twitch の新着を毎朝 Discord に配信。サーバー不要で GitHub Actions の cron だけで動作 | GitHub Actions, RSS, Twitch API |
| [snapclip](snapclip/) | スクショのスタック撮影・スクロールキャプチャ（テンプレートマッチングで結合）・クリップボード履歴キュー | OpenCV, mss, pywin32 |
| [pdfcraft](pdfcraft/) | 分割・結合・圧縮・墨消し・OCR・Markdown 抽出までローカル完結の PDF ツールキット | PyMuPDF, EasyOCR |

## 開発の進め方 / How these were built

多くのプロジェクトは **Claude Code（AI コーディングエージェント）と協働** して開発しています。

1. 自分で要件・設計を仕様書にまとめる（[`docs/specs/*_detail.md`](docs/specs/)）
2. Claude Code が実装し、設計判断・未検証部分をレポートにまとめる（[`docs/specs/*_report.md`](docs/specs/)）
3. レポートとコードをレビューし、実機で動作確認・修正する

実機（カメラ、Unity Editor など）がない環境で検証できなかった部分は、各 README に「未検証」と明記しています。
今後のアイデアは [`docs/roadmap.txt`](docs/roadmap.txt) にあります。

## プロジェクト一覧 / Projects

### 通知・監視・情報収集 / Notifications & monitoring

- [`notify/`](notify/) — Multi-channel notifications (Slack, Discord, LINE Messaging API, desktop) built on `reqretry`, plus a `@notify_on_complete` decorator for long-running scripts. See [notify/README.md](notify/README.md) for install and usage.
- [`feedwatch/`](feedwatch/) — Watches RSS/Atom feeds (YouTube channels, blogs, etc.) and Twitch channels (via the Twitch API's Get Streams endpoint, since Twitch has no RSS) for new items, notifying via `notify` with no duplicate notifications (tracked in SQLite). `feedwatch add`/`add-twitch`/`list`/`remove` manage watches; `feedwatch start` polls on a loop (default every 10 min). See [feedwatch/README.md](feedwatch/README.md) for install and usage.
- [`sitewatch/`](sitewatch/) — Companion to `feedwatch` for sites without RSS: watches a CSS-selected element on a page (via BeautifulSoup) and notifies via `notify` when its content hash changes. Each watch enforces its own minimum polling interval (default 30 min) to avoid hammering a site. See [sitewatch/README.md](sitewatch/README.md) for install and usage.
- [`mailwatch/`](mailwatch/) — Polls Gmail (OAuth2, `gmail.readonly` scope) for messages matching sender/subject/body rules defined in YAML, and fires `notify()` (Slack/Discord/etc.) per matching rule with sender, subject, and received time; deduplicates processed messages in SQLite and can optionally save attachments to a configurable folder. See [mailwatch/README.md](mailwatch/README.md) for install, Gmail API setup, and usage.
- [`ytdigest/`](ytdigest/) — Daily YouTube/Twitch new-content digest posted to Discord, run entirely from a GitHub Actions cron (no always-on server). Pulls new uploads from YouTube channel RSS feeds and live/VOD status from the Twitch API, posts a numbered new-content list to a Discord webhook, parses `delete 1,3`-style dismiss replies via a Discord bot, and auto-archives undismissed items after 3 days. State is a SQLite file committed back to the repo after each run. See [ytdigest/README.md](ytdigest/README.md) for full setup (Discord bot + webhooks, Twitch Client Credentials, required GitHub Actions secrets).

### AI・LLM連携・検索 / AI, LLM & search

- [`claude-bridge/`](claude-bridge/) — Always-on Discord bot for remote-controlling Claude Code: instructions posted to a configured channel run headlessly via `claude -p` (with per-project session continuity through `--resume`), replying with progress ("編集中: foo.py", parsed from `--output-format stream-json`), a `diff`/`summary` result view, and a `git push --force`/`rm -rf`-style pre-flight keyword guard that requires a `yes` reply before running. Sender/channel/project-path allowlists, a per-run timeout, single-worker queueing with a `stop` cancel command, and a SQLite run history round out the safety/ops model; `claude-bridge start`/`status`/`ping` manage it. See [claude-bridge/README.md](claude-bridge/README.md) for setup (Discord bot creation, `bridge.yaml`) and the security tradeoffs of running Claude Code with permission checks bypassed.
- [`notesearch/`](notesearch/) — Local semantic + keyword hybrid search over a notes directory (nothing leaves the machine except an explicit `--ask`): `notesearch "query"` JIT-syncs (mtime-diffed re-embedding via a multilingual SentenceTransformers model into ChromaDB) then fuses vector similarity with a freshly-rebuilt BM25 keyword index, opening an interactive results TUI (jump to the matched line in your editor) by default, or `--copy` to put a RAG-formatted prompt on the clipboard, or `--ask` to send that prompt straight to Gemini and print the answer. `--dir`/`--days` scope results; `sync`/`clean`/`daemon start` manage the index directly; optional `auto_convert_pdf` routes `.pdf` files through [`pdfcraft`](pdfcraft/) first. See [notesearch/README.md](notesearch/README.md) for install and usage.
- [`slidecraft/`](slidecraft/) — Converts LLM-generated structured HTML (`<section class="slide">` per slide, `<h1>`/`<ul>`/`<p>`/`<img>`/`<aside class="notes">`, with inline `<strong>`/`<em>` runs) into an editable PPTX via `python-pptx`; `slidecraft --get-prompt` prints the exact system prompt to paste into an LLM alongside your source material, and `slidecraft generate slides.html --template company_master.pptx -o out.pptx` builds the deck against your own template (fonts/background/placeholder layout), auto-picking each slide's layout by name (image vs. text-only) and falling back to python-pptx's own built-in default template when no `--template` is given. See [slidecraft/README.md](slidecraft/README.md) for install and usage.
- [`wikigen/`](wikigen/) — Static searchable wiki site generator: `wikigen build` turns a folder of Markdown notes (with frontmatter tags and `[[wikilinks]]`) into a self-contained HTML site with a folder-tree sidebar, tag pages, and client-side full-text search; `wikigen serve` previews it locally. See [wikigen/README.md](wikigen/README.md) for install and usage.

### システム管理・ファイル整理・自動化 / System & file automation

- [`sysreport/`](sysreport/) — PC startup health check: `sysreport run` snapshots storage free space (via `diskcheck`), battery level/charging state and CPU/memory usage (via `psutil`), and sends a one-line emoji summary through `notify`; thresholds are configurable with an opt-in `--highlight-warnings` mark, and `sysreport setup-autostart` registers a Windows Task Scheduler logon task to run it automatically. See [sysreport/README.md](sysreport/README.md) for install and usage.
- [`diskcheck/`](diskcheck/) — Storage management CLI with three independent subcommands: `diskcheck scan` ranks folders/files by size (tree view, JSON, or an interactive drill-down browser), `diskcheck dupes` finds duplicate files by SHA256 content hash (size-bucketed for performance) with an interactive keep/delete flow, and `diskcheck stale` flags old installers/temp files by extension and last-access age (extension list configurable via `confload`). All three default to listing candidates only; nothing is deleted without explicit confirmation or `--yes`. See [diskcheck/README.md](diskcheck/README.md) for install and usage.
- [`projarchive/`](projarchive/) — Frees disk space held by unused project venvs while keeping them reproducible: `projarchive archive-project` deletes a project's `venv`/`.venv` after ensuring a `requirements.txt` exists (auto-generated via `pip freeze` if missing; aborts without deleting anything if that fails), `projarchive restore-project` rebuilds it from `requirements.txt` (via `uv` if available, else `python -m venv` + `pip`), and `projarchive list-projects` shows every project under a parent directory with its venv size and archive status. Both archive and list support `--all`/batch use on a whole parent directory, and archiving supports `--dry-run`. See [projarchive/README.md](projarchive/README.md) for install and usage.
- [`snapclip/`](snapclip/) — Windows screenshot + clipboard extension: `snapclip daemon start` registers global hotkeys for stack-capture screenshots (auto-saved with Markdown/LaTeX figure syntax pushed to the clipboard) and hold-to-drag scroll capture (OpenCV template-matching stitches the scrolled frames into one tall image), sharing one FIFO paste queue with regular OS copies so `Alt+Shift+V` pops back whatever was copied or captured, oldest first; `snapclip web` full-page-captures a URL via headless Chromium, and `snapclip history` is an fzf-style incremental search over a persistent SQLite clipboard log. See [snapclip/README.md](snapclip/README.md) for install and usage.
- [`devfind/`](devfind/) — File-search wrapper CLI that combines `fd` (filename match), `ripgrep` (content match), and `fzf` (labeled `[NAME]`/`[CONTENT]` picker with a `bat`/`cat` preview pane) to find "I remember a file like this" candidates across configurable folders (`confload`-backed YAML config; default `Downloads`/`Documents`, with excludes like `venv`/`node_modules`/`.git`); prints the selected path to stdout for piping into an editor. `fd`/`ripgrep`/`fzf` are external prerequisites, not bundled dependencies. See [devfind/README.md](devfind/README.md) for install and usage.
- [`translate-comments/`](translate-comments/) — CLI that translates source code comments (`#`, `//`, `/* */`, and Python docstrings) between Japanese, English, and French via DeepL, leaving the code itself untouched; supports appending translations inline or writing separate per-language file copies, plus recursive batch processing with a preview-then-confirm/`--dry-run` workflow. See [translate-comments/README.md](translate-comments/README.md) for install and usage.

### 画像・動画・PDF・コンピュータビジョン / Image, video, PDF & computer vision

- [`gazemouse/`](gazemouse/) — Hands-free desktop control: eye tracking (MediaPipe FaceLandmarker iris, EMA-smoothed) moves the cursor, a right-hand fist open<->closed edge drives mouse press/release (so a quick close+open is a click and staying closed while looking elsewhere is a drag, for free), a sustained 2-second eye closure (or a deliberate wink) triggers a screenshot via [`snapclip`](snapclip/), and head tilt (not gaze, to avoid fighting the cursor) scrolls. `gazemouse calibrate` walks through a 4-corner gaze calibration; `gazemouse start` runs the loop with an Esc kill switch, a separate ON/OFF toggle hotkey, and auto-pause when your face leaves frame. See [gazemouse/README.md](gazemouse/README.md) for install and usage — including why this one, unlike the rest of this repo, could not be verified against real hardware in this environment.
- [`batchimg/`](batchimg/) — OpenCV-based batch resize/rename/trim CLI for images and videos, with a preview-then-confirm workflow and a non-destructive default output directory. See [batchimg/README.md](batchimg/README.md) for install and usage.
- [`cvprep/`](cvprep/) — OpenCV preprocessing one-liners (resize, normalize, ROI crop, edge detection, ...) driven by YAML presets. See [cvprep/README.md](cvprep/README.md) for install and usage.
- [`pdfcraft/`](pdfcraft/) — Local-only PDF toolkit (PyMuPDF-based, nothing uploaded anywhere): page operations (`split`/`merge`/`extract`/`delete`/`remove-blank`/`rotate`/`nup`/`compress`), image↔PDF report generation (`pdf-to-img`/`img-to-pdf`/`report` from a CSV/YAML batch list), security (`encrypt`/`decrypt`/`sanitize`/`redact` by keyword, regex, or coordinates), and layout-aware extraction (`extract-md` with noise filtering, `ocr` via EasyOCR, `annotations`, `watermark`, `page-numbers`). See [pdfcraft/README.md](pdfcraft/README.md) for install and usage.
- [`unity-cv-bridge/`](unity-cv-bridge/) — Real-time Unity <-> OpenCV video bridge over ZeroMQ (JPEG frames out via PUB/SUB, JSON results back via REQ/REP). Both sides implemented and protocol-verified; Unity-side C# not yet compiled inside an actual Unity Editor (none installed here). See [unity-cv-bridge/README.md](unity-cv-bridge/README.md).

### 開発支援・タスク管理・実験管理 / Developer tools

- [`devtoolbox/`](devtoolbox/) — CLI toolbox (`projinit` project scaffolder, `snip` snippet manager). See [devtoolbox/README.md](devtoolbox/README.md) for install and usage.
- [`kanbancli/`](kanbancli/) — Offline, Markdown-file-backed kanban CLI (`- [status] content [priority] @add:... @due:... @recur:... @depends:... #tag id:xxxx`, one task per line): `add`/`update`/`list`/`export`/`archive`, subtasks via indentation, `@depends` blocking (surfaced by `list --available`), `@recur` auto-generating the next occurrence on completion (due date anchored to the original `@due`, not the completion date), and `remind`/`setup-autostart` for daily due-date notifications via `notify`. Hybrid file resolution: a local `.kanban.md` (cwd or a parent directory) if one exists, else the global `~/.config/kanbancli/tasks.md`. Supersedes [`devtoolbox`](devtoolbox/)'s SQLite-backed `todo` (kept for backward compatibility). See [kanbancli/README.md](kanbancli/README.md) for install and usage.
- [`tunelab/`](tunelab/) — Hyperparameter tuning experiment manager: define a search space + training command in YAML, and `tune run` drives Optuna/scikit-optimize/random search through trials automatically, persisting results to SQLite. See [tunelab/README.md](tunelab/README.md) for install and usage.

### ローカル共有・ネットワーク / Local sharing

- [`airshare/`](airshare/) — AirDrop-like local web server (FastAPI) for sending files between iPhone and PC over the same Wi-Fi network: `airshare start` prints an ASCII QR code of the LAN URL for iPhone Safari to scan, with LAN-only access, an optional passcode, and a Windows desktop `.bat` shortcut generator. `airshare watch start` is its companion Inbox-watching daemon: debounced auto-routing of newly-received files by extension, an optional per-extension shell hook (e.g. auto-compress a routed PDF via `pdfcraft`), a clickable Windows toast per batch (`winotify`), and daily stale-file cleanup to the Recycle Bin (`send2trash`); `airshare watch status`/`clean` check on or manually trigger it. See [airshare/README.md](airshare/README.md) for install and usage.

### 共通ライブラリ / Shared libraries

- [`confload/`](confload/) — Unified YAML/JSON config loader with dict + attribute access, environment variable overrides, and `${VAR}` reference resolution. See [confload/README.md](confload/README.md) for install and usage.
- [`reqretry/`](reqretry/) — Thin wrapper around `requests` with configurable exponential-backoff retries (timeouts, 5xx, connection errors) and a default request timeout. See [reqretry/README.md](reqretry/README.md) for install and usage.

## License

[MIT](LICENSE)
