from __future__ import annotations

import base64
import io

import qrcode


def render_ascii(url: str) -> str:
    """Render the URL as an ASCII-art QR code for terminal display."""
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    buf = io.StringIO()
    qr.print_ascii(out=buf, tty=False)
    return buf.getvalue()


def render_png_data_uri(url: str) -> str:
    """Render the URL as a QR code PNG, encoded as a data: URI for embedding in HTML."""
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
