from __future__ import annotations

import pytest
import responses

from sitewatch.scraper import ElementNotFoundError, ScrapeError, scrape_selector

URL = "https://example.test/page"


@responses.activate
def test_scrape_selector_extracts_text_and_html(no_sleep):
    html = '<html><body><div id="price">$9.99</div></body></html>'
    responses.add(responses.GET, URL, status=200, body=html, content_type="text/html")

    content = scrape_selector(URL, "#price")

    assert content.text == "$9.99"
    assert content.html == '<div id="price">$9.99</div>'


@responses.activate
def test_scrape_selector_missing_element_raises(no_sleep):
    html = "<html><body><div id='other'>hi</div></body></html>"
    responses.add(responses.GET, URL, status=200, body=html, content_type="text/html")

    with pytest.raises(ElementNotFoundError):
        scrape_selector(URL, "#price")


@responses.activate
def test_scrape_selector_http_error_raises(no_sleep):
    for _ in range(4):  # reqretry default: 1 initial attempt + 3 retries, all 500
        responses.add(responses.GET, URL, status=500)

    with pytest.raises(ScrapeError):
        scrape_selector(URL, "#price")


@responses.activate
def test_content_hash_stable_across_irrelevant_markup_changes(no_sleep):
    """Hash is based on text, so attribute-only churn (e.g. a tracking id) shouldn't count as a change."""
    html_v1 = '<div id="price" data-track="abc">$9.99</div>'
    html_v2 = '<div id="price" data-track="xyz">$9.99</div>'
    responses.add(responses.GET, URL, status=200, body=f"<html><body>{html_v1}</body></html>")
    responses.add(responses.GET, URL, status=200, body=f"<html><body>{html_v2}</body></html>")

    first = scrape_selector(URL, "#price")
    second = scrape_selector(URL, "#price")

    assert first.content_hash == second.content_hash


@responses.activate
def test_content_hash_changes_when_text_changes(no_sleep):
    responses.add(responses.GET, URL, status=200, body='<html><body><div id="price">$9.99</div></body></html>')
    responses.add(responses.GET, URL, status=200, body='<html><body><div id="price">$8.99</div></body></html>')

    first = scrape_selector(URL, "#price")
    second = scrape_selector(URL, "#price")

    assert first.content_hash != second.content_hash
