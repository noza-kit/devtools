from __future__ import annotations

import json
import logging
from typing import List

import typer
import zmq

from uzbridge import protocol
from uzbridge.config import MockConfig, ServerConfig
from uzbridge.mock import MockSender
from uzbridge.ops import color_range, contour_detect
from uzbridge.pipeline import Pipeline
from uzbridge.server import BridgeServer

app = typer.Typer(help="Unity <-> OpenCV video bridge over ZeroMQ", add_completion=True)

STEPS = {
    "contours": contour_detect,
    "color_range": color_range,
}


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _build_pipeline(step_names: List[str]) -> Pipeline:
    pipeline = Pipeline()
    for name in step_names:
        func = STEPS.get(name)
        if func is None:
            typer.secho(
                f"Unknown step {name!r}. Available: {', '.join(sorted(STEPS))}",
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=1)
        pipeline.add_step(func, name=name)
    return pipeline


@app.command()
def serve(
    bind_host: str = typer.Option("*", help="Host/interface to bind sockets on"),
    sub_port: int = typer.Option(5555, help="Port to receive JPEG frames on (SUB)"),
    rep_port: int = typer.Option(5556, help="Port to serve results on (REP)"),
    step: List[str] = typer.Option(
        ["contours"], "--step", help="Pipeline step to run (repeatable, runs in order)"
    ),
    log_interval: float = typer.Option(5.0, help="Seconds between FPS/latency log lines"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
) -> None:
    """Run the bridge server: receive frames, process them, serve results."""
    _configure_logging(verbose)
    config = ServerConfig(
        bind_host=bind_host, sub_port=sub_port, rep_port=rep_port, log_interval=log_interval
    )
    pipeline = _build_pipeline(step)
    BridgeServer(config, pipeline).run_forever()


@app.command()
def mock(
    connect_host: str = typer.Option("localhost", help="Host running the bridge server"),
    pub_port: int = typer.Option(5555, help="Server's SUB port to publish frames to"),
    source: str = typer.Option(
        "webcam:0", help="'webcam:<index>' or a path to a static image file"
    ),
    max_fps: float = typer.Option(15.0, help="Maximum send rate"),
    jpeg_quality: int = typer.Option(80, min=1, max=100, help="JPEG compression quality"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
) -> None:
    """Publish frames from a webcam or image file, standing in for Unity."""
    _configure_logging(verbose)
    config = MockConfig(
        connect_host=connect_host,
        pub_port=pub_port,
        source=source,
        max_fps=max_fps,
        jpeg_quality=jpeg_quality,
    )
    MockSender(config).run_forever()


@app.command()
def fetch(
    host: str = typer.Option("localhost", help="Host running the bridge server"),
    rep_port: int = typer.Option(5556, help="Server's REP port"),
    timeout: float = typer.Option(3.0, help="Seconds to wait for a reply"),
) -> None:
    """One-shot REQ client: fetch and print the latest pipeline result.

    Useful for exercising the REP side by hand before Unity is wired up.
    """
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, int(timeout * 1000))
    socket.setsockopt(zmq.LINGER, 0)
    socket.connect(f"tcp://{host}:{rep_port}")
    socket.send(protocol.encode_request())
    try:
        reply = socket.recv()
    except zmq.Again:
        typer.secho(f"No reply within {timeout}s", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    finally:
        socket.close(0)
        context.term()
    typer.echo(json.dumps(json.loads(reply), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    app()
