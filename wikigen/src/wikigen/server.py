from __future__ import annotations

import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def make_server(directory: Path, port: int = 0) -> ThreadingHTTPServer:
    """Build (but don't start) an HTTP server rooted at `directory`.

    Passing port=0 lets the OS pick a free port, useful for tests.
    """
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(directory))
    return ThreadingHTTPServer(("127.0.0.1", port), handler)


def serve_directory(directory: Path, port: int = 8000) -> None:
    """Serve `directory` at http://127.0.0.1:<port>/ until interrupted."""
    httpd = make_server(directory, port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
