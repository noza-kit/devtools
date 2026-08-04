from __future__ import annotations

import threading
import urllib.request
from pathlib import Path

from wikigen.server import make_server


def test_make_server_serves_directory_contents(tmp_path: Path):
    (tmp_path / "hello.txt").write_text("hello wikigen", encoding="utf-8")

    httpd = make_server(tmp_path, port=0)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/hello.txt", timeout=5) as resp:
            body = resp.read().decode("utf-8")
        assert body == "hello wikigen"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)
