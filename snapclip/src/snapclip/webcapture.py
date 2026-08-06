from __future__ import annotations

from pathlib import Path


def capture_full_page(url: str, output_path: Path, viewport_width: int = 1280) -> Path:
    """Render `url` headlessly and save a full-page (not just-viewport)
    screenshot to `output_path`. Needs the `web` extra
    (`pip install -e ".[web]"`) plus a one-time `playwright install
    chromium` to fetch the actual browser binary — imported lazily so
    the rest of snapclip works without either."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ImportError(
            'Web capture requires the "web" extra: pip install -e ".[web]", '
            "then run `playwright install chromium` once to fetch the browser binary."
        ) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": viewport_width, "height": 800})
            page.goto(url, wait_until="networkidle")
            page.screenshot(path=str(output_path), full_page=True)
        finally:
            browser.close()
    return output_path
