# slidecraft

Converts LLM-generated, structured HTML into an editable PPTX — the
LLM writes the *logical structure* of a slide deck (title, bullets,
notes) in HTML, and slidecraft turns that into `.pptx` slides you can
open in PowerPoint or Google Slides and finish by hand, optionally
starting from your own template file so the output already carries
your fonts/background/branding.

- [Install](#install)
- [Workflow](#workflow)
- [HTML ⇔ slide mapping](#html--slide-mapping)
- [`slidecraft generate`](#slidecraft-generate)
- [Layout auto-selection](#layout-auto-selection)
- [Known limitations](#known-limitations)
- [Development](#development)

## Install

```bash
cd slidecraft
pip install -e ".[dev]"
```

From GitHub (this package lives in the `slidecraft/` subdirectory of the repo):

```bash
pip install "git+https://github.com/noza-kit/devtools.git#subdirectory=slidecraft"
```

## Workflow

```bash
# 1. Get the system prompt slidecraft expects, and copy it to the clipboard
slidecraft --get-prompt | clip

# (Paste it into ChatGPT/Claude/etc. along with your source material or
#  outline, and save what comes back as slides.html)

# 2. Generate a PPTX, using your own template for fonts/branding
slidecraft generate slides.html --template company_master.pptx -o final_presentation.pptx

# 3. Or, without a template, using a minimal built-in default
slidecraft generate slides.html -o quick_draft.pptx
```

`--get-prompt` prints the exact structural rules the parser expects (a
condensed version of [HTML ⇔ slide mapping](#html--slide-mapping)
below) as a ready-to-paste LLM system prompt — see
`slidecraft/prompt.py`'s `SYSTEM_PROMPT` for the full text.

## HTML ⇔ slide mapping

```html
<div class="presentation">
  <section class="slide">
    <h1>市場調査のサマリー</h1>
    <div class="content">
      <ul>
        <li><strong>ターゲット層:</strong> 20代〜30代の若年層</li>
        <li><em>課題:</em> 認知度の低下が顕著</li>
      </ul>
      <img src="./images/graph1.png" alt="年代別認知度グラフ">
    </div>
    <aside class="notes">
      ここは重要なスライドです。特に若年層の認知度低下について強調してください。
    </aside>
  </section>
</div>
```

| Tag | Becomes |
| --- | --- |
| `<section class="slide">` | One new PPTX slide per section |
| `<h1>` | The slide's title placeholder text (one per section; a second `<h1>` is ignored) |
| `<ul>`/`<ol>` + `<li>` | Bullet paragraphs; a `<ul>`/`<ol>` nested inside an `<li>` becomes a deeper indent level |
| `<p>` | A plain (non-bulleted) paragraph |
| `<strong>`/`<em>` (anywhere inside a `<li>` or `<p>`) | Bold/italic on just that run of text within the paragraph — not the whole paragraph |
| `<img src="..." alt="...">` | An image, scaled (aspect ratio preserved, never stretched) to fit the slide's image region; `src` is resolved relative to the HTML file's own directory |
| `<aside class="notes">` | The slide's speaker notes |

Only `<div class="content">`'s direct structural content
(`<ul>`/`<ol>`/`<p>`/`<img>`, with `<strong>`/`<em>` as inline
decoration inside list items and paragraphs) is interpreted — heading
levels below `<h1>` (`<h2>`, `<h3>`, ...) aren't currently mapped to
anything.

## `slidecraft generate`

```
slidecraft generate HTML -o OUTPUT.pptx [--template TEMPLATE.pptx]
```

- `HTML` — the structured HTML file (see above).
- `-o`/`--output` — where to write the generated `.pptx`.
- `--template` — an existing `.pptx` to build on top of. Its fonts,
  background, and slide-layout placeholder positions carry over to
  every generated slide, exactly like starting a new deck from that
  file in PowerPoint. **Without `--template`**, slidecraft uses
  [`python-pptx`](https://python-pptx.readthedocs.io/)'s own bundled
  default template — a plain white background with standard fonts —
  rather than shipping a second, redundant default `.pptx` of our own;
  this already satisfies "never errors just because no template was
  given."

## Layout auto-selection

Each slide picks its base layout automatically, by name, from whichever
template is in use (your `--template`, or the built-in default):

- **Has an `<img>`** → tries `Two Content`, then `Comparison`, then
  `Content with Caption`, then `Picture with Caption`, in that order.
- **Text only** → tries `Title and Content`, then `Section Header`,
  then `Title Slide`.
- **Fallback**, if none of those names exist in the template → the
  first layout that has a title placeholder plus at least one other
  placeholder; if even that fails, the template's very first layout.

Once a layout is picked: the title placeholder gets the `<h1>` text;
the first body-type placeholder (`BODY`/`OBJECT`/`SUBTITLE`) gets the
bulleted/paragraph content; for an image, a second `OBJECT`/`PICTURE`/
`BODY`-type placeholder's position and size is reused (the empty
placeholder shape itself is removed and replaced with the actual
picture) — or, if the picked layout doesn't have a spare placeholder to
reuse, the image is placed in a fixed region covering the slide's right
40% instead. A second and third image on the same slide stack
vertically below the first, splitting the remaining space evenly.

## Known limitations

- **Layout name matching is a heuristic, not a guarantee.** These
  layout names (`Two Content`, `Title and Content`, ...) are
  PowerPoint's own built-in template naming convention, which most
  templates — including ones exported from Google Slides or built from
  scratch — follow, but a template with entirely custom/renamed/
  Japanese-named layouts will fall through to the generic fallback
  (title + first available body placeholder), which still produces a
  usable slide, just not necessarily the most visually fitting layout
  for that content. Getting this fully right for an arbitrary template
  would need actual visual/geometric analysis of each layout, which was
  judged out of scope for this round.
- **No heading levels below `<h1>`.** `<h2>`/`<h3>` inside
  `<div class="content">` are currently ignored by the parser (not
  mapped to sub-headings or styled text) — only `<h1>` (title),
  `<ul>`/`<ol>`/`<p>`/`<img>`, and inline `<strong>`/`<em>` are
  interpreted.
- **Tables, charts, and other rich content types** in the source HTML
  aren't supported — only text (with bold/italic runs), bullet
  hierarchy, and images.

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests build small in-memory-style HTML fixtures directly (see
`tests/conftest.py`) and verify against real `python-pptx` `Presentation`
objects — no binary fixture files, no external LLM calls involved
(there's nothing to call; slidecraft only *generates the prompt* you'd
paste into an LLM yourself, it doesn't call one).
