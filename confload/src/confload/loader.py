from __future__ import annotations

import copy
import json
import os
import re
from collections.abc import Mapping as ABCMapping
from pathlib import Path
from typing import Any, Iterator, Optional

import yaml

_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_.]*)(?::-([^}]*))?\}")
_MISSING = object()


class ConfigError(Exception):
    pass


class Config(ABCMapping):
    """Read-only, dict-like view over config data with attribute access.

    Nested mappings (including ones inside lists) are wrapped recursively, so
    `config.model.name` works the same as `config["model"]["name"]`. Falls
    back to `Mapping`'s `keys`/`items`/`get`/`__contains__` etc., which take
    priority over attribute access for a config key of the same name.
    """

    def __init__(self, data: dict):
        self.__dict__["_data"] = {k: _wrap(v) for k, v in data.items()}

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __getattr__(self, name: str) -> Any:
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(
                f"Config has no key {name!r} (available: {sorted(self._data)})"
            ) from None

    def __repr__(self) -> str:
        return f"Config({self._data!r})"

    def to_dict(self) -> dict:
        return {k: _unwrap(v) for k, v in self._data.items()}


def _wrap(value: Any) -> Any:
    if isinstance(value, dict):
        return Config(value)
    if isinstance(value, list):
        return [_wrap(v) for v in value]
    return value


def _unwrap(value: Any) -> Any:
    if isinstance(value, Config):
        return value.to_dict()
    if isinstance(value, list):
        return [_unwrap(v) for v in value]
    return value


def load_config(
    path: str | Path,
    *,
    env_prefix: str = "APP",
    required: Optional[list[str]] = None,
) -> Config:
    """Load a YAML or JSON config file into a `Config` object.

    Resolution order: read file -> apply `{env_prefix}_*` env var overrides ->
    resolve `${...}` references -> validate `required` dot-path keys.
    """
    path = Path(path)
    raw = _read_file(path)

    if not isinstance(raw, dict):
        raise ConfigError(f"Config file must contain a top-level mapping/object: {path}")

    merged = _apply_env_overrides(raw, env_prefix)
    resolved = _resolve_variables(merged, path)
    _check_required(resolved, required or [], path)

    return Config(resolved)


def _read_file(path: Path) -> Any:
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")

    if suffix in (".yaml", ".yml"):
        try:
            return yaml.safe_load(text) or {}
        except yaml.YAMLError as exc:
            raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc
    elif suffix == ".json":
        if not text.strip():
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"Invalid JSON in {path}: {exc}") from exc
    else:
        raise ConfigError(
            f"Unsupported config file extension {suffix!r} (expected .yaml, .yml, or .json): {path}"
        )


def _apply_env_overrides(data: dict, env_prefix: str) -> dict:
    result = copy.deepcopy(data)
    prefix = f"{env_prefix}_"

    for env_name, raw_value in os.environ.items():
        if not env_name.startswith(prefix):
            continue
        key_path = env_name[len(prefix):]
        parts = [p.lower() for p in key_path.split("__") if p]
        if not parts:
            continue
        _set_nested(result, parts, _coerce_env_value(raw_value))

    return result


def _set_nested(data: dict, parts: list[str], value: Any) -> None:
    current = data
    for part in parts[:-1]:
        existing = current.get(part)
        if not isinstance(existing, dict):
            existing = {}
            current[part] = existing
        current = existing
    current[parts[-1]] = value


def _coerce_env_value(raw_value: str) -> Any:
    """Parse an env var string as a YAML scalar so overrides keep the type
    implied by the value (int/float/bool/null), falling back to the raw
    string on parse failure or for lists/mappings (unsupported over env)."""
    if raw_value == "":
        return ""
    try:
        parsed = yaml.safe_load(raw_value)
    except yaml.YAMLError:
        return raw_value
    if isinstance(parsed, (dict, list)):
        return raw_value
    return parsed


def _resolve_variables(data: dict, source: Path) -> dict:
    cache: dict[str, Any] = {}
    in_progress: set[str] = set()

    def flat_get(dotted_key: str) -> Any:
        node: Any = data
        for part in dotted_key.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return _MISSING
        return node

    def resolve_key(dotted_key: str) -> Any:
        if dotted_key in cache:
            return cache[dotted_key]
        if dotted_key in in_progress:
            raise ConfigError(f"Circular variable reference involving '{dotted_key}' in {source}")
        raw_value = flat_get(dotted_key)
        if raw_value is _MISSING:
            return _MISSING

        in_progress.add(dotted_key)
        try:
            resolved = resolve_value(raw_value, dotted_key)
        finally:
            in_progress.discard(dotted_key)
        cache[dotted_key] = resolved
        return resolved

    def resolve_value(value: Any, dotted_key: str) -> Any:
        if isinstance(value, str):
            return resolve_string(value, dotted_key)
        if isinstance(value, dict):
            return {k: resolve_value(v, f"{dotted_key}.{k}") for k, v in value.items()}
        if isinstance(value, list):
            return [resolve_value(v, dotted_key) for v in value]
        return value

    def resolve_string(text: str, dotted_key: str) -> str:
        def replace(match: re.Match) -> str:
            name, default = match.group(1), match.group(2)
            resolved = resolve_key(name)
            if resolved is _MISSING:
                env_value = os.environ.get(name)
                if env_value is not None:
                    resolved = env_value
                elif default is not None:
                    resolved = default
                else:
                    raise ConfigError(
                        f"Unresolved variable '${{{name}}}' referenced in "
                        f"'{dotted_key}' (not found in config or environment; source: {source})"
                    )
            return str(resolved)

        return _VAR_PATTERN.sub(replace, text)

    return {k: resolve_key(k) for k in data}


def _check_required(data: dict, required: list[str], source: Path) -> None:
    missing = []
    for dotted_key in required:
        node: Any = data
        found = True
        for part in dotted_key.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                found = False
                break
        if not found:
            missing.append(dotted_key)

    if missing:
        raise ConfigError(
            f"Missing required config key(s): {', '.join(missing)} (source: {source})"
        )
