# tunelab

Hyperparameter tuning experiment manager. Define a search space and a
training command/function once in a YAML config, and `tune run` drives
Optuna (or scikit-optimize, or a plain random/grid search) through many
trials automatically, persisting every result to SQLite so you can resume,
compare, and export the best run later.

## Install

```bash
cd tunelab
pip install -e ".[dev]"
```

Optional extras:

```bash
pip install -e ".[skopt]"      # backend: skopt (scikit-optimize Bayesian search)
pip install -e ".[viz]"        # `tune plot` (Optuna/plotly HTML report)
pip install -e ".[dashboard]"  # `tune dashboard` (optuna-dashboard web UI)
```

## Quick start

```bash
tune init my-experiment          # writes my-experiment.yaml
# edit the space/objective in my-experiment.yaml, then:
tune run my-experiment.yaml
tune status my-experiment
tune best my-experiment --top 5
```

## Config

```yaml
study: mnist-cnn
direction: maximize          # maximize | minimize
backend: optuna               # optuna | skopt | random | grid

budget:
  n_trials: 50
  # timeout: 3600              # seconds, optional
  n_jobs: 4                    # parallel workers (optuna/random backends only)

space:
  lr:
    type: float
    low: 1.0e-5
    high: 1.0e-1
    log: true
  batch_size:
    type: int
    low: 16
    high: 256
    step: 16
  optimizer:
    type: categorical
    choices: [adam, sgd, rmsprop]

objective:
  mode: command                # command | callable
  command: "python train.py --lr {lr} --batch-size {batch_size} --optimizer {optimizer} --result-file {result_file}"
  result_file: json            # train.py must write {"value": <float>} to this path
  # result_regex: "val_acc:\s*([0-9.]+)"   # alternative: parse a number from stdout instead
  timeout_per_trial: 1800
  working_dir: .
```

Literal `{`/`}` in `command` must be doubled (`{{`/`}}`) since it's a
`str.format` template — only do this if your training script's own
command-line syntax needs a brace.

For an in-process function instead of a subprocess, use callable mode:

```yaml
objective:
  mode: callable
  entrypoint: mypackage.train:objective   # def objective(params: dict) -> float
```

## Backends

| backend | engine | notes |
| --- | --- | --- |
| `optuna` (default) | Optuna's TPE sampler | Best default; supports `n_jobs` parallelism, resumable, per-trial progress logging built in |
| `random` | numpy | Zero extra dependencies; supports `n_jobs` (batched via a thread pool) |
| `grid` | numpy (`itertools.product`) | Exhaustive search over discrete params (`int` with `step`, `categorical`); a `float` param without a step can't be griddded |
| `skopt` | scikit-optimize Bayesian (`Optimizer.ask/tell`) | Requires the `skopt` extra; runs sequentially (`n_jobs` is ignored) |

All backends write into the same Optuna SQLite study, so `status`/`best`/
`list`/`export`/`plot` work identically regardless of which one produced the
trials.

## CLI

```bash
tune init <name> [-o config.yaml] [--force]      # scaffold a config
tune run <config.yaml> [--n-trials N] [--timeout SEC] [--n-jobs N] [--fresh]
tune status <study>
tune best <study> [--top N]
tune list <study> [--state complete|fail] [--sort number|value|duration]
tune export <study> [-o results.csv]
tune plot <study> [-o report.html]               # requires the viz extra
tune dashboard <study>                            # requires the dashboard extra
tune studies                                      # list known study names
tune delete <study> [--yes]
```

Studies persist under `~/.tunelab/studies/<name>.db` (relocatable via the
`TUNELAB_HOME` env var). Re-running `tune run` against the same study name
resumes it; pass `--fresh` to discard prior trials and start over.

## Development

```bash
pip install -e ".[dev,skopt,viz]"
pytest
```
