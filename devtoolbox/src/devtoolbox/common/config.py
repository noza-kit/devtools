from __future__ import annotations

from dataclasses import dataclass, field

import yaml

from devtoolbox.common.paths import devtoolbox_home


@dataclass
class ProjinitConfig:
    default_lang: str | None = None
    default_license: str | None = None
    default_author: str | None = None


@dataclass
class SnipConfig:
    default_tags: list[str] = field(default_factory=list)


@dataclass
class DotsyncConfig:
    source_dir: str | None = None


@dataclass
class Config:
    projinit: ProjinitConfig = field(default_factory=ProjinitConfig)
    snip: SnipConfig = field(default_factory=SnipConfig)
    dotsync: DotsyncConfig = field(default_factory=DotsyncConfig)


def config_path():
    return devtoolbox_home() / "config.yaml"


def load_config() -> Config:
    path = config_path()
    if not path.exists():
        return Config()

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    projinit_raw = raw.get("projinit") or {}
    snip_raw = raw.get("snip") or {}
    dotsync_raw = raw.get("dotsync") or {}

    return Config(
        projinit=ProjinitConfig(**projinit_raw),
        snip=SnipConfig(**snip_raw),
        dotsync=DotsyncConfig(**dotsync_raw),
    )
