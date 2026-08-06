# pdfcraft

A local-only PDF toolkit: no file is ever sent to an external server (no
"I Love PDF"-style upload). Split/merge/compress/rotate/N-up page
operations, image↔PDF report generation, password/redaction/metadata
security tools, and layout-aware Markdown/OCR extraction, all as one CLI
built on [PyMuPDF](https://pymupdf.readthedocs.io/).

- [Install](#install)
- [Module A — page operations](#module-a--page-operations)
- [Module B — image ↔ PDF](#module-b--image--pdf)
- [Module C — security](#module-c--security)
- [Module D — extraction & decoration](#module-d--extraction--decoration)
- [Known limitations & heuristics](#known-limitations--heuristics)
- [Development](#development)

## Install

```bash
cd pdfcraft
pip install -e ".[dev]"
```

OCR (`pdfcraft ocr`) needs the optional `ocr` extra — it pulls in
[EasyOCR](https://github.com/JaidedAI/EasyOCR) and PyTorch (a few hundred
MB), so it's kept out of the default install:

```bash
pip install -e ".[ocr]"
```

From GitHub (this package lives in the `pdfcraft/` subdirectory of the repo):

```bash
pip install "git+https://github.com/noza-kit/devtools.git#subdirectory=pdfcraft"
```

Every command takes `INPUT` as a positional path and `-o`/`--output` (or
`--output-dir` for commands that produce multiple files) for where to
write the result — originals are never modified in place.

## Module A — page operations

### `split`

```bash
pdfcraft split input.pdf --ranges 1-3 --ranges 5,8-10 -o out/
pdfcraft split input.pdf -o out/                       # no --ranges: one file per page
```

`--ranges` is repeatable; each occurrence becomes one output file
(`<stem>_part01.pdf`, ...). Omit it to split one file per page instead
(`<stem>_page0001.pdf`, ...).

### `merge`

```bash
pdfcraft merge doc1.pdf doc2.pdf -o merged.pdf
pdfcraft merge doc1.pdf doc2.pdf -o merged.pdf --page-numbers --toc
pdfcraft merge doc1.pdf doc2.pdf -o merged.pdf --no-toc
```

Concatenates files in the given order. `--toc` (default on) adds one
top-level bookmark per source file, named after its filename stem,
pointing at the first page it contributed. `--page-numbers` additionally
stamps `N/total` into the footer of the merged result (see
[`page-numbers`](#page-numbers)).

### `extract` / `delete`

```bash
pdfcraft extract input.pdf --pages "1-3,5" -o output.pdf   # keep only these pages
pdfcraft delete input.pdf --pages "1-3,5" -o output.pdf    # remove these pages
```

Page specs are 1-indexed, comma-separated, and support ranges
(`"1-3,5,8-10"`). `delete` refuses to write an empty document if every
page is selected for removal.

### `remove-blank`

```bash
pdfcraft remove-blank input.pdf -o output.pdf
```

Drops pages that have no embedded images and no extractable text — a
heuristic, not a pixel-level "is this page visually empty" check (see
[Known limitations](#known-limitations--heuristics)).

### `rotate`

```bash
pdfcraft rotate input.pdf --degrees 90 -o output.pdf
pdfcraft rotate input.pdf --degrees 180 --pages "2,4" -o output.pdf
```

`--degrees` (90/180/270, or a negative/multiple-of-90 equivalent) is
*added* to each page's existing rotation, not set absolutely. `--pages`
restricts which pages rotate; default is all pages.

### `nup` — N-up / 面付け

```bash
pdfcraft nup input.pdf --n 2 -o output.pdf   # 2 source pages per output page (1x2)
pdfcraft nup input.pdf --n 4 -o output.pdf   # 4 source pages per output page (2x2)
```

Only `--n 2` and `--n 4` are supported (fixed 1x2 / 2x2 grids on A4) —
arbitrary NxM layouts were judged out of scope for how this tool is
actually used (handout printing).

### `compress`

```bash
pdfcraft compress input.pdf -o output.pdf --quality medium   # default
pdfcraft compress input.pdf -o output.pdf --quality low      # smallest, most lossy
pdfcraft compress input.pdf -o output.pdf --quality high     # least lossy
```

Recompresses embedded images via PyMuPDF's `rewrite_images` (downsampling
+ JPEG re-encode) and runs structural cleanup (duplicate-object removal,
stream deflation) on save. Quality levels map to (target DPI, JPEG
quality): high = (200, 85), medium = (150, 70), low = (100, 50); images
already at or near the target resolution are left untouched rather than
upscaled or needlessly re-encoded. The CLI prints the before/after size
and the percentage saved.

## Module B — image ↔ PDF

### `pdf-to-img`

```bash
pdfcraft pdf-to-img input.pdf -o out_dir/
pdfcraft pdf-to-img input.pdf -o out_dir/ --pages "1-3" --format jpeg --dpi 300
```

Renders each selected page (default: all) to its own image file. `--dpi`
defaults to 200.

### `img-to-pdf`

```bash
pdfcraft img-to-pdf photo1.jpg photo2.jpg -o output.pdf
pdfcraft img-to-pdf photo1.jpg photo2.jpg -o output.pdf --title "Results" --caption "Fig. 1"
```

One image per page, centered and scaled to fit within the page margins
(aspect ratio preserved, never stretched/cropped), with an optional
shared title/caption stamped on every page.

### `report` — batch report generation

```bash
pdfcraft report --config experiments.csv -o experiment_report.pdf
pdfcraft report --config experiments.yaml -o experiment_report.pdf --grid 2
```

Reads a CSV or YAML list of `{image_path (or path), title, caption}` and
generates one titled/captioned PDF report. `--grid` controls images per
page: `1` (default — one image, its own title top + caption bottom, per
page) or `2`/`4` (a grid of images per page, each with its own caption
underneath; no page-level title in grid mode since each cell has one).

CSV columns: `image_path` (or `path`), `title`, `caption` (title/caption
optional). YAML: a list of mappings with the same keys. Relative image
paths are resolved against the config file's own directory, not the
current working directory.

```yaml
# experiments.yaml
- path: ./figs/run1_loss.png
  title: "Run 1: training loss"
  caption: "lr=1e-3, batch=32"
- path: ./figs/run2_loss.png
  title: "Run 2: training loss"
  caption: "lr=5e-4, batch=64"
```

## Module C — security

### `encrypt` / `decrypt`

```bash
pdfcraft encrypt input.pdf -o output.pdf --user-password mypassword
pdfcraft encrypt input.pdf -o output.pdf --user-password mypass --owner-password ownerpass --allow-modification
pdfcraft decrypt input.pdf -o output.pdf --password mypassword
```

AES-256 encryption. `--user-password` (prompted interactively if
omitted) is required to open the file at all; `--owner-password`
(defaults to the user password) additionally gates the permission bits.
Printing and copying are allowed by default; pass `--allow-modification`
to also allow editing/annotating (off by default — a viewing-only
restriction is the common case). `decrypt` accepts either the user or
owner password.

### `sanitize`

```bash
pdfcraft sanitize input.pdf -o output.pdf
```

Clears all standard metadata fields (author, creator, producer, creation/
modification dates, ...) and any embedded XML metadata stream.

### `redact`

```bash
pdfcraft redact input.pdf -o output.pdf --keywords "山田太郎"
pdfcraft redact input.pdf -o output.pdf --pattern "[A-Z]{2}-\d{4}"
pdfcraft redact input.pdf -o output.pdf --box "100,200,300,400" --page 1
pdfcraft redact input.pdf -o output.pdf --keywords "山田太郎" --keywords "田中一郎" --pattern "\d{3}-\d{4}-\d{4}"
```

Permanently removes matched content — both the visible black box *and*
the underlying text/data (via PyMuPDF's redaction annotations, not a
cosmetic overlay). `--keywords` (repeatable) does a literal case-
sensitive search; `--pattern` is a regex matched **per word** (PDF text
extraction is word-granular, so a pattern spanning whitespace, like a
name with a space in it, won't match — this is fine for the common case
of phone numbers/IDs/codes, which are single tokens). `--box` takes
`"x0,y0,x1,y1"` in PDF points and is repeatable; all `--box` values in
one invocation apply to the single page given by `--page` (1-indexed,
default 1) — redacting boxes across multiple pages needs one `--box`
per page in a single run isn't supported; run the command again for a
different page. At least one of `--keywords`/`--pattern`/`--box` is
required.

Scanned image-only PDFs (no text layer) are **not** supported by
`--keywords`/`--pattern`, since there's no extractable text to search —
OCR the file first (a different tool; text recognized by OCR isn't fed
back into the PDF's text layer) or use `--box` with known coordinates
instead.

## Module D — extraction & decoration

### `extract-md`

```bash
pdfcraft extract-md paper.pdf -o output.md
pdfcraft extract-md paper.pdf -o output.md --skip-image-pages 50 --min-text-chars 30
pdfcraft extract-md paper.pdf -o output.md --no-skip-headers --no-skip-toc
```

Extracts a structure-preserving Markdown document: heading level is
inferred from font size relative to the document's most common ("body")
font size (largest distinct size → `#`, next → `##`, capped at `####`).
By default, this also filters out:

- **Recurring headers/footers** — text repeating in the top/bottom 8% of
  the page across ≥50% of pages (≥3-page documents only). Digit runs are
  normalized before comparing, so a page-numbered footer like "Page 1" /
  "Page 2" / ... is still recognized as one recurring pattern. Disable
  with `--no-skip-headers`/`--no-skip-footers`.
- **TOC-style dot-leader lines** (`"Introduction ..... 12"`) —
  `--no-skip-toc`.
- **Isolated short numeric lines** (chart axis labels etc., e.g. `"42%"`
  on a line by itself) — always on unless you pass a page-level workaround
  (see limitations below).
- **High-image-coverage pages**, via `--skip-image-pages PCT` (e.g. `50`
  skips any page where images cover ≥50% of the page area) — off by
  default.
- **Thin-text pages** (cover pages, pure-figure pages), via
  `--min-text-chars N` — off by default (`0`).

### `ocr`

```bash
pdfcraft ocr scanned.pdf -o output.txt --lang jpn+eng
pdfcraft ocr scanned.pdf -o output.txt --lang eng --pages "1-5"
```

OCRs a scanned/image-only PDF via EasyOCR (needs `pip install -e
".[ocr]"`, see [Install](#install)). `--lang` uses Tesseract-style `+`-
joined codes (`jpn`, `eng`, `fra`, `chi_sim`, `chi_tra`, `kor`, ...),
mapped internally to EasyOCR's own codes; an unrecognized code is passed
through as-is, so an EasyOCR-native code also works directly. The OCR
backend sits behind a small `OCREngine` interface
(`pdfcraft/ocr.py`) specifically so a `TesseractOCREngine` can be added
later without touching `ocr_extract()` or the CLI, if EasyOCR's accuracy
or model size turns out to be a problem in practice.

### `annotations`

```bash
pdfcraft annotations input.pdf                        # prints a table
pdfcraft annotations input.pdf -o annotations.json     # writes JSON instead
```

Extracts highlights, comments, and other markup annotations (page,
type, author, content, rect) in page order.

### `watermark`

```bash
pdfcraft watermark input.pdf -o output.pdf --text "社外秘" --opacity 0.3
pdfcraft watermark input.pdf -o output.pdf --image logo.png --opacity 0.15
```

`--text` draws a diagonal (45°) watermark across every page; `--image`
centers and scales an image to fit the page instead. Exactly one of
`--text`/`--image` is required. `--opacity` (0-1, default 0.3) is real
alpha blending — a genuine `fill_opacity` for text, and a baked-in alpha
channel (via Pillow) for images, not a color/brightness approximation.

### `page-numbers`

```bash
pdfcraft page-numbers input.pdf -o output.pdf
pdfcraft page-numbers input.pdf -o output.pdf --format "Page {n} of {total}" --position bottom-right
```

Stamps a page number into the footer (or `--position top-center` for the
header) of every page. `--format` is a `str.format()` template with `n`
(1-indexed) and `total`. `--position`: `bottom-center` (default),
`bottom-left`, `bottom-right`, `top-center`.

## Known limitations & heuristics

`extract-md`'s noise filtering is intentionally simple rather than a
full layout-analysis model, per the spec's "simple heuristics are fine"
scope. Concretely, in rough priority order for a future pass:

1. **Isolated-number filtering is page-blind.** A line like `"42%"` is
   dropped as chart-axis noise on *every* page it appears on, even if
   it's legitimately the entire content of a one-line answer. A better
   version would only apply this on pages already flagged as
   image-heavy (cross-reference with `_image_coverage_pct`), rather than
   globally.
2. **Header/footer detection needs ≥3 pages and an exact (post-
   normalization) text match.** A 1-2 page document gets no
   header/footer filtering at all, and a header that changes its
   *wording* per section (not just a page number) won't be recognized
   as recurring. A fuzzy/prefix match (e.g. common leading words) would
   catch more real-world cases.
3. **Heading levels are purely font-size-relative**, with no
   awareness of numbering (`"1.2.3 Foo"`) or indentation, so a
   large-font pull-quote or a big figure caption can be misclassified
   as a heading. Cross-checking against text length/position (headings
   are usually short and left-aligned) would help.
4. **TOC detection is per-line**, not per-page — a real table-of-
   contents page is still emitted, just with its dot-leader lines
   stripped, which can look like a list of bare titles rather than
   being skipped as a whole page. Detecting "most lines on this page
   match the TOC pattern" and skipping the whole page would be more
   correct.
5. **`remove-blank`'s blank-page heuristic** treats "no image + no
   extractable text" as blank — a page with only vector line art (a
   flowchart border, a signature line) is not caught by this and
   won't be removed, and conversely a page whose only content is
   invisible/degenerate text objects would incorrectly be dropped.

None of these block real usage; they're listed here as the concrete
next steps if extraction quality on a specific document turns out to
matter.

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests build small in-memory-style PDFs with PyMuPDF directly (see
`tests/conftest.py`'s `sample_pdf` fixture) rather than depending on
fixture binary files. `ocr.py`'s tests inject a fake `OCREngine`
(see `tests/test_ocr.py`) rather than exercising the real EasyOCR
backend, since EasyOCR needs its optional extra installed and downloads
model weights on first use — not appropriate for a unit test. To
manually verify the real OCR path: `pip install -e ".[ocr]"`, then run
`pdfcraft ocr` against a scanned PDF and eyeball the output.
