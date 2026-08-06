from __future__ import annotations

import hashlib
from dataclasses import dataclass

import reqretry
from bs4 import BeautifulSoup


class ScrapeError(Exception):
    pass


class ElementNotFoundError(ScrapeError):
    pass


@dataclass
class ScrapedContent:
    """The text/HTML of one CSS-selected element, plus a hash of its text for change detection."""

    text: str
    html: str

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


def scrape_selector(url: str, selector: str) -> ScrapedContent:
    """Fetch `url` (retried via reqretry) and return the text/HTML of the first element matching `selector`."""
    try:
        resp = reqretry.get(url)
        resp.raise_for_status()
    except Exception as exc:
        raise ScrapeError(f"failed to fetch {url}: {exc}") from exc

    soup = BeautifulSoup(resp.text, "html.parser")
    element = soup.select_one(selector)
    if element is None:
        raise ElementNotFoundError(f"selector {selector!r} matched nothing on {url}")

    return ScrapedContent(text=element.get_text(strip=True), html=str(element))
