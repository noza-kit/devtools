# hobby

Personal projects, one subdirectory per project.

## Projects

- [`devtoolbox/`](devtoolbox/) — CLI toolbox (`projinit` project scaffolder, `snip` snippet manager). See [devtoolbox/README.md](devtoolbox/README.md) for install and usage.
- [`cvprep/`](cvprep/) — OpenCV preprocessing one-liners (resize, normalize, ROI crop, edge detection, ...) driven by YAML presets. See [cvprep/README.md](cvprep/README.md) for install and usage.
- [`tunelab/`](tunelab/) — Hyperparameter tuning experiment manager: define a search space + training command in YAML, and `tune run` drives Optuna/scikit-optimize/random search through trials automatically, persisting results to SQLite. See [tunelab/README.md](tunelab/README.md) for install and usage.
- [`confload/`](confload/) — Unified YAML/JSON config loader with dict + attribute access, environment variable overrides, and `${VAR}` reference resolution. See [confload/README.md](confload/README.md) for install and usage.
- [`reqretry/`](reqretry/) — Thin wrapper around `requests` with configurable exponential-backoff retries (timeouts, 5xx, connection errors) and a default request timeout. See [reqretry/README.md](reqretry/README.md) for install and usage.
