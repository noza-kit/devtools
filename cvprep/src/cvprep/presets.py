from __future__ import annotations

import yaml

from cvprep.paths import presets_path

DEFAULT_PRESETS_YAML = """\
presets:
  edge_prep:
    - op: grayscale
    - op: blur
      ksize: 5
    - op: canny
      threshold1: 50
      threshold2: 150

  resize_normalize:
    - op: resize
      width: 224
      height: 224
    - op: normalize
      mean: [0.485, 0.456, 0.406]
      std: [0.229, 0.224, 0.225]

  thumbnail:
    - op: resize
      scale: 0.25
"""


class PresetNotFoundError(Exception):
    pass


def load_presets() -> dict[str, list[dict]]:
    path = presets_path()
    if not path.exists():
        return {}

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return raw.get("presets") or {}


def get_preset(name: str) -> list[dict]:
    presets = load_presets()
    if name not in presets:
        raise PresetNotFoundError(f"Preset {name!r} not found")
    return presets[name]


def list_preset_names() -> list[str]:
    return sorted(load_presets().keys())


def init_presets_file(force: bool = False) -> bool:
    """Write the starter presets.yaml. Returns False without writing if it
    already exists and force is False."""
    path = presets_path()
    if path.exists() and not force:
        return False
    path.write_text(DEFAULT_PRESETS_YAML, encoding="utf-8")
    return True
