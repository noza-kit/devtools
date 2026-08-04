from __future__ import annotations

from airshare.qr import render_ascii, render_png_data_uri


def test_render_ascii_contains_block_characters() -> None:
    output = render_ascii("http://192.168.1.10:8000/")
    assert len(output) > 0
    assert "\n" in output


def test_render_png_data_uri_is_a_data_url() -> None:
    uri = render_png_data_uri("http://192.168.1.10:8000/")
    assert uri.startswith("data:image/png;base64,")
