# confload

A small, dependency-light config loader that unifies YAML/JSON files and
environment variable overrides behind one `Config` object, with both dict
and attribute access.

## Install

```bash
cd confload
pip install -e ".[dev]"
```

From GitHub (this package lives in the `confload/` subdirectory of the repo):

```bash
pip install "git+https://github.com/noza-kit/devtools.git#subdirectory=confload"
```

## Usage

```python
from confload import load_config, ConfigError

config = load_config("config.yaml")

config.learning_rate      # attribute access
config["learning_rate"]   # dict-style access
config.model.name         # nested mappings are wrapped recursively
config.to_dict()          # back to a plain dict/list structure
```

```yaml
# config.yaml
base_dir: /data
dataset_path: ${base_dir}/train   # -> "/data/train"
api_key: ${API_KEY:-changeme}     # from env var API_KEY, else "changeme"
learning_rate: 0.01
model:
  name: resnet50
```

Both `.yaml`/`.yml` and `.json` files are supported, picked by extension.

## Environment variable overrides

Any `{env_prefix}_*` environment variable (prefix defaults to `APP`) overrides
the matching config key. Nested keys are addressed with a double underscore:

```bash
APP_LEARNING_RATE=0.02 python train.py   # overrides learning_rate -> 0.02 (float)
APP_MODEL__NAME=resnet101 python train.py  # overrides model.name
```

Override values are parsed as YAML scalars so they keep the type implied by
the value (`"0.02"` -> `float`, `"true"` -> `bool`, `"4"` -> `int`), falling
back to a plain string when that fails. Use a custom prefix per call:

```python
config = load_config("config.yaml", env_prefix="MYAPP")
```

## `${VAR}` references

String values may reference other config keys (dotted path for nested keys)
or environment variables with `${NAME}`, resolved in that order, with an
optional default via `${NAME:-default}`. References are resolved *after* env
overrides are applied, so a reference picks up the overridden value.
Circular or unresolved references raise `ConfigError`.

## Required keys

```python
config = load_config("config.yaml", required=["learning_rate", "model.name"])
# ConfigError: Missing required config key(s): model.name (source: config.yaml)
```

## Development

```bash
pip install -e ".[dev]"
pytest
```
