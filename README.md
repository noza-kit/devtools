# hobby

Personal projects, one subdirectory per project.

## Projects

- [`devtoolbox/`](devtoolbox/) — CLI toolbox (`projinit` project scaffolder, `snip` snippet manager). See [devtoolbox/README.md](devtoolbox/README.md) for install and usage.
- [`cvprep/`](cvprep/) — OpenCV preprocessing one-liners (resize, normalize, ROI crop, edge detection, ...) driven by YAML presets. See [cvprep/README.md](cvprep/README.md) for install and usage.
- [`tunelab/`](tunelab/) — Hyperparameter tuning experiment manager: define a search space + training command in YAML, and `tune run` drives Optuna/scikit-optimize/random search through trials automatically, persisting results to SQLite. See [tunelab/README.md](tunelab/README.md) for install and usage.
- [`confload/`](confload/) — Unified YAML/JSON config loader with dict + attribute access, environment variable overrides, and `${VAR}` reference resolution. See [confload/README.md](confload/README.md) for install and usage.
- [`reqretry/`](reqretry/) — Thin wrapper around `requests` with configurable exponential-backoff retries (timeouts, 5xx, connection errors) and a default request timeout. See [reqretry/README.md](reqretry/README.md) for install and usage.
- [`unity-cv-bridge/`](unity-cv-bridge/) — Real-time Unity <-> OpenCV video bridge over ZeroMQ (JPEG frames out via PUB/SUB, JSON results back via REQ/REP). Both sides implemented and protocol-verified; Unity-side C# not yet compiled inside an actual Unity Editor (none installed here). See [unity-cv-bridge/README.md](unity-cv-bridge/README.md).
- [`wikigen/`](wikigen/) — Static searchable wiki site generator: `wikigen build` turns a folder of Markdown notes (with frontmatter tags and `[[wikilinks]]`) into a self-contained HTML site with a folder-tree sidebar, tag pages, and client-side full-text search; `wikigen serve` previews it locally. See [wikigen/README.md](wikigen/README.md) for install and usage.
