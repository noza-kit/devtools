from __future__ import annotations

import pytest
import responses

from feedwatch.feeds import FeedFetchError, fetch_entries, normalize_feed_source

CHANNEL_ID = "UCabcdefghijklmnopqrstuv"
FEED_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"

YOUTUBE_FEED_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns="http://www.w3.org/2005/Atom">
  <link rel="self" href="{FEED_URL}"/>
  <title>Example Channel</title>
  <entry>
    <id>yt:video:VIDEOID1</id>
    <yt:videoId>VIDEOID1</yt:videoId>
    <yt:channelId>{CHANNEL_ID}</yt:channelId>
    <title>Video Title 1</title>
    <link rel="alternate" href="https://www.youtube.com/watch?v=VIDEOID1"/>
    <published>2026-08-01T00:00:00+00:00</published>
  </entry>
  <entry>
    <id>yt:video:VIDEOID2</id>
    <yt:videoId>VIDEOID2</yt:videoId>
    <yt:channelId>{CHANNEL_ID}</yt:channelId>
    <title>Video Title 2</title>
    <link rel="alternate" href="https://www.youtube.com/watch?v=VIDEOID2"/>
    <published>2026-08-02T00:00:00+00:00</published>
  </entry>
</feed>
"""


@responses.activate
def test_fetch_entries_parses_youtube_feed(no_sleep):
    responses.add(responses.GET, FEED_URL, status=200, body=YOUTUBE_FEED_XML, content_type="application/atom+xml")

    entries = fetch_entries(FEED_URL)

    assert [e.item_id for e in entries] == ["yt:video:VIDEOID1", "yt:video:VIDEOID2"]
    assert entries[0].title == "Video Title 1"
    assert entries[0].link == "https://www.youtube.com/watch?v=VIDEOID1"


@responses.activate
def test_fetch_entries_http_error_raises(no_sleep):
    for _ in range(4):  # reqretry default: 1 initial attempt + 3 retries, all 500
        responses.add(responses.GET, FEED_URL, status=500)

    with pytest.raises(FeedFetchError):
        fetch_entries(FEED_URL)


@responses.activate
def test_fetch_entries_unparsable_body_raises(no_sleep):
    responses.add(responses.GET, FEED_URL, status=200, body="not xml at all {{{")

    with pytest.raises(FeedFetchError):
        fetch_entries(FEED_URL)


def test_normalize_feed_source_expands_bare_channel_id():
    assert normalize_feed_source(CHANNEL_ID) == FEED_URL


def test_normalize_feed_source_passes_through_url_unchanged():
    assert normalize_feed_source(FEED_URL) == FEED_URL


def test_normalize_feed_source_passes_through_non_youtube_url():
    other = "https://example.test/feed.xml"
    assert normalize_feed_source(other) == other
