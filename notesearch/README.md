# notesearch

Local semantic + keyword hybrid search over a notes directory — no data
ever leaves your machine (embedding, vector storage, and keyword
indexing are all local). Optionally connects to Gemini for a RAG
answer, but that's the only network call this tool ever makes, and
only when you explicitly pass `--ask`.

- [Install](#install)
- [Config](#config)
- [`notesearch "query"`](#notesearch-query)
- [`notesearch sync` / `clean`](#notesearch-sync--clean)
- [`notesearch daemon start`](#notesearch-daemon-start)
- [Gemini setup (`--ask`)](#gemini-setup---ask)
- [Architecture](#architecture)
- [Known limitations](#known-limitations)
- [Development](#development)

## Install

```bash
cd notesearch
pip install -e "../confload" -e "../reqretry"   # local deps, not on PyPI
pip install -e ".[dev]"
```

This pulls in `sentence-transformers` (+ PyTorch) and `chromadb` — a few
hundred MB to ~1.5GB depending on platform/CPU-vs-GPU wheels, plus
another ~470MB the first time the embedding model itself is downloaded
from HuggingFace on first real use (not at install time). Nothing is
downloaded just by installing or running `--help`/`sync`/`clean` on an
empty index — the embedding model only loads lazily, the moment
something actually needs to be embedded.

## Config

`~/.notesearch/config.yaml` (or `--config path/to/file.yaml` on any
command):

```yaml
target_dirs:
  - ~/Documents
  - ~/notes
exclude:
  - venv
  - .venv
  - node_modules
  - __pycache__
  - .git
extensions: [.md, .txt, .csv]
chunk_size: 500
chunk_overlap: 50
auto_convert_pdf: false
editor_command: "code -g {path}:{line}"
db_dir: ~/.notesearch/db
gemini_api_key: ...   # see "Gemini setup" below; env var GEMINI_API_KEY also works
```

Every key is optional — an unset key falls back to the default shown
above. No config file at all is also fine (same defaults, `target_dirs:
[~/Documents]`).

**PDF files** are skipped entirely unless `auto_convert_pdf: true`, in
which case each `.pdf` under `target_dirs` is converted to a sibling
`.md` via [`pdfcraft`](../pdfcraft)'s `extract_markdown()` (only if
pdfcraft is installed — silently skipped, not an error, if it isn't)
and that `.md` is indexed instead. Conversion only re-runs when the
`.pdf` is newer than its `.md`.

## `notesearch "query"`

```bash
notesearch "Dockerのビルドエラーの解決策"
notesearch "認証APIの仕様" --dir project_A --days 30
notesearch "Nginxのリバースプロキシ設定" --top 5 --copy
notesearch "Dockerのビルドエラーの解決策" --ask
```

Every search runs JIT sync first (see [Architecture](#architecture)) —
only files that are new or changed since the last search get
(re-)embedded, so a search over an already-synced directory costs one
mtime comparison per file, not a full re-index.

- No flags: opens an interactive TUI (↑/↓ to move, Enter to jump to
  that chunk's line in your editor, Esc to quit).
- `--dir NAME` restricts to sources whose parent folder is named
  `NAME`; `--days N` restricts to files modified in the last N days;
  both compose (`--dir` AND `--days`).
- `--top N` (default 5) — how many results to return.
- `--copy` — formats the results as a RAG prompt (see below) and
  copies it to the clipboard, skipping the TUI. Use this to paste
  straight into ChatGPT/Claude/etc. yourself.
- `--ask` — same RAG prompt, but with your actual query as the
  question, sent straight to the Gemini API, with the answer printed
  to the terminal. See [Gemini setup](#gemini-setup---ask).

### RAG prompt format

```
以下の参考資料を基に、私の質問に回答してください。
---
[資料1: project_A/setup_guide.md]
(チャンクのテキスト)
---
[資料2: memo/error_logs.txt]
(チャンクのテキスト)
---
質問：[ここにプロンプトを入力]
```

(`--ask` fills the last line with your real query instead of the
placeholder.)

### Hybrid search

Every query runs two independent retrievals over the same chunk
corpus — a [ChromaDB](https://www.trychroma.com/) vector similarity
search (via a multilingual [SentenceTransformers](https://www.sbert.net/)
model, `paraphrase-multilingual-MiniLM-L12-v2`) and a
[BM25](https://en.wikipedia.org/wiki/Okapi_BM25) keyword search (via
[`rank_bm25`](https://github.com/dorianbrown/rank_bm25), rebuilt fresh
from ChromaDB's already-persisted chunk texts on each query) — then
fuses the two rankings by min-max normalizing each to [0, 1] and taking
a weighted sum (50/50 by default). This means a query that's mostly
"the right words" (a variable name, an error code) and a query that's
mostly "the right meaning" (a vague paraphrase) both have a real chance
of surfacing the right chunk.

## `notesearch sync` / `clean`

```bash
notesearch sync    # run JIT sync once, without also searching
notesearch clean   # purge index entries for files that no longer exist on disk
```

`clean` is separate from `sync` because sync only ever adds/updates —
it never notices a file that was deleted or renamed since the last
sync (there's nothing to compare a missing file's mtime against).
`clean` walks the index the other direction: for every source path
currently indexed, check whether that file still exists, and drop its
chunks if not.

## `notesearch daemon start`

```bash
notesearch daemon start
notesearch daemon start --interval 10
```

The alternative to per-search JIT sync: watches `target_dirs` for
filesystem changes (via [`watchdog`](https://github.com/gorakhargosh/watchdog))
and re-syncs automatically in the background, coalesced to at most once
per `--interval` seconds (default 5) rather than once per individual
file-save event. Useful if you want the index to always be current
without waiting for the next search to trigger a sync — otherwise, JIT
sync (the default, no daemon needed) is simpler and sufficient for most
use.

## Gemini setup (`--ask`)

1. Go to [Google AI Studio](https://aistudio.google.com/apikey) and
   sign in with a Google account.
2. Click **Create API key** (a free tier is available with generous
   rate limits for personal use; no credit card required to start).
3. Copy the key and either:
   - set it as an environment variable: `export GEMINI_API_KEY=...`, or
   - add it to your config file: `gemini_api_key: ...` (see
     [Config](#config) above) — checked first, before the env var.

```bash
notesearch "Dockerのビルドエラーの解決策" --ask
```

Requests go straight to `generativelanguage.googleapis.com` (the
default model is `gemini-2.0-flash`) via [`reqretry`](../reqretry), so
a transient network error/5xx gets retried with backoff before being
treated as a failure.

## Architecture

| Module | Responsibility |
| --- | --- |
| `chunking.py` | Heading-based section split, falling back to fixed-size+overlap for long sections (or heading-less files); tracks each chunk's approximate source line number |
| `scanner.py` | Walks `target_dirs` for eligible files (respecting `exclude`/`extensions`); optional PDF→Markdown conversion via `pdfcraft` |
| `embeddings.py` | Lazy-loaded `SentenceTransformerEmbedder` behind an `Embedder` protocol |
| `vectordb.py` | ChromaDB-backed chunk store: upsert (delete-then-add, so a shrunk document doesn't leave stale trailing chunks), delete, and vector query |
| `bm25index.py` | In-memory BM25 index, rebuilt from ChromaDB's full corpus on each query |
| `hybrid.py` | Min-max normalize + weighted-sum fusion of the two rankings |
| `search.py` | Orchestrates JIT sync → vector query → BM25 query (both scoped by `--dir`/`--days`) → fusion |
| `sync.py` | JIT sync (mtime diff → re-embed changed/new) and `clean` (purge deleted-file entries) |
| `watcher.py` | Optional `watchdog`-based background daemon, debounced |
| `ragprompt.py` | The RAG prompt template + clipboard copy (`pyperclip`) |
| `gemini.py` | Gemini API client (`reqretry`-backed) for `--ask` |
| `editor.py` | Builds the jump-to-editor command from a configurable template |
| `tui.py` | `msvcrt`-based (Windows-only) interactive results browser |
| `cli.py` | Typer CLI; a custom `TyperGroup` subclass makes the bare `notesearch "query"` invocation work alongside the `sync`/`clean`/`daemon` subcommands (see below) |

## Known limitations

- **A query that's exactly `sync`, `clean`, or `daemon` gets
  intercepted by that subcommand instead of searched for.** Making
  `notesearch "query"` work with no keyword, per the spec's own CLI
  examples, while also supporting named subcommands, means the first
  bare word has to be checked against the registered command names
  first — a real (if narrow) ambiguity inherent to that design, not an
  oversight. Work around it with `notesearch search sync` (the `search`
  command's name explicitly, if you ever actually need to search for
  one of those exact words).
- **Hybrid search score fusion is unweighted-equal by default** (50/50
  vector/BM25) with no CLI flag to adjust it per-query — `hybrid.
  combine_results()`'s `vector_weight`/`bm25_weight` parameters exist
  and are called from `search.py`, but aren't yet exposed as CLI
  options.
- **The `--dir` filter matches on the immediate parent folder name
  only** (e.g. `project_A/setup.md` matches `--dir project_A`, but
  `project_A/sub/setup.md` does not) — not a full path-prefix match.

## Development

```bash
pip install -e "../confload" -e "../reqretry"
pip install -e ".[dev]"
pytest
```

- Real, no mocking: chunking, scanning, config loading, BM25, hybrid
  fusion, the RAG prompt template, the editor-command builder, and
  ChromaDB itself (via a `FakeEmbedder` that hashes text into small
  deterministic vectors instead of loading the real ~470MB
  multilingual model — real vector storage/retrieval/deletion
  semantics are exercised for real, just not real semantic similarity).
- Mocked: `notesearch.gemini.ask()`'s HTTP call (via `responses`, same
  pattern used elsewhere in this repo, e.g. translate-comments' DeepL
  tests), and `notesearch.tui.run_search_tui()`/`notesearch.watcher.
  run_daemon()` in CLI-level tests (interactive keypress loop and a
  real filesystem watcher, respectively — neither is meaningfully
  testable in an automated suite; `filter`/state-machine-style logic
  that doesn't itself need the OS hook is tested directly instead,
  same approach as this repo's other daemon-style tools).
- Not exercised at all in this round: the real `SentenceTransformerEmbedder`
  (needs downloading actual model weights) and the real Gemini API
  (needs a live key and a network call) — both are straightforward to
  verify manually: run `notesearch "query"` against a real notes
  directory once dependencies are installed, and `notesearch "query"
  --ask` with `GEMINI_API_KEY` set.
