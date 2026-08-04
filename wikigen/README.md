# wikigen

A static, searchable wiki site generator: point it at a folder of Markdown
notes and it produces a self-contained HTML site with a folder-structure
sidebar, `[[wikilink]]` support, tag pages, and client-side full-text search
that needs no server or backend to run.

## Install

```bash
cd wikigen
pip install -e ".[dev]"
```

From GitHub (this package lives in the `wikigen/` subdirectory of the repo):

```bash
pip install "git+https://github.com/noza-kit/devtools.git#subdirectory=wikigen"
```

## Usage

```bash
wikigen build ./my-notes --output ./site
wikigen serve ./site
```

Open the printed `http://127.0.0.1:8000/` URL, or open `site/index.html`
directly in a browser — search and navigation both work without a server,
since the search index is a plain `<script>`-included JS file rather than
something fetched over XHR.

### `wikigen build`

```
wikigen build SOURCE_DIR [--output/-o PATH] [--title TEXT]
```

- Recursively converts every `*.md` file under `SOURCE_DIR` to HTML,
  mirroring the source folder structure in the output.
- `--output` / `-o` sets the output folder (default: `./site`).
- `--title` sets the site title shown in the sidebar (default: `Wiki`).
- If `SOURCE_DIR/index.md` exists it becomes the home page; otherwise a
  simple auto-generated index listing every page is written instead.

### `wikigen serve`

```
wikigen serve [DIRECTORY] [--port/-p PORT]
```

Serves a previously built site folder (default: `./site`) at
`http://127.0.0.1:8000/` for local preview.

## Markdown features

### Frontmatter (title + tags)

```markdown
---
title: My Note
tags: [python, notes]
---

# My Note

Body text...
```

- `title` overrides the page title (falls back to the first `# Heading`,
  then the filename).
- `tags` accepts a YAML list or a comma-separated string. Every tag gets a
  generated `tags/<tag>.html` listing page, plus a `tags/index.html`
  overview of all tags.

### Wikilinks

```markdown
See [[Other Note]] or [[Other Note|a custom label]].
```

Targets are matched (case-insensitively) against a page's `title`, its
filename, or its path without extension — so ambiguous note names can be
disambiguated as `[[folder/note]]`. Links resolve to a path relative to the
current page, so the output works whether it's opened straight off disk or
served over HTTP. Unresolved targets are still rendered, with a
`wikilink-broken` CSS class instead of an `href`, rather than failing the
build.

### Search

Every build writes `assets/search-index.js` (the page contents as a plain
JS object literal) and `assets/search.js` (a small vanilla-JS filter over
it, wired to the sidebar search box on every page). There's no server-side
component and no fetch/XHR call, so it works from a `file://` URL too.

## Development

```bash
pip install -e ".[dev]"
pytest
```
