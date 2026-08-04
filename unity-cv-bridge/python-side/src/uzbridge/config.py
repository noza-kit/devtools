from __future__ import annotations

from dataclasses import dataclass

DEFAULT_SUB_PORT = 5555
DEFAULT_REP_PORT = 5556
DEFAULT_MAX_FPS = 15.0
DEFAULT_JPEG_QUALITY = 80


@dataclass
class ServerConfig:
    """Bridge server settings: binds a SUB socket for frames and a REP
    socket for results."""

    bind_host: str = "*"
    sub_port: int = DEFAULT_SUB_PORT
    rep_port: int = DEFAULT_REP_PORT
    log_interval: float = 5.0

    @property
    def sub_address(self) -> str:
        return f"tcp://{self.bind_host}:{self.sub_port}"

    @property
    def rep_address(self) -> str:
        return f"tcp://{self.bind_host}:{self.rep_port}"


@dataclass
class MockConfig:
    """Mock sender settings: connects to a running server's SUB socket and
    stands in for the Unity side."""

    connect_host: str = "localhost"
    pub_port: int = DEFAULT_SUB_PORT
    source: str = "webcam:0"
    max_fps: float = DEFAULT_MAX_FPS
    jpeg_quality: int = DEFAULT_JPEG_QUALITY

    @property
    def pub_address(self) -> str:
        return f"tcp://{self.connect_host}:{self.pub_port}"
