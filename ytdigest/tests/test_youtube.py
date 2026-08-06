from __future__ import annotations

import responses

from ytdigest.youtube import YOUTUBE_FEED_URL, YouTubeError, fetch_channel_videos

SAMPLE_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015"
      xmlns:media="http://search.yahoo.com/mrss/"
      xmlns="http://www.w3.org/2005/Atom">
 <id>yt:channel:UCxxxx</id>
 <yt:channelId>UCxxxx</yt:channelId>
 <title>Example Channel</title>
 <author><name>Example Channel</name><uri>https://www.youtube.com/channel/UCxxxx</uri></author>
 <entry>
  <id>yt:video:vid1</id>
  <yt:videoId>vid1</yt:videoId>
  <yt:channelId>UCxxxx</yt:channelId>
  <title>First Video</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=vid1"/>
  <author><name>Example Channel</name></author>
  <published>2026-08-01T12:00:00+00:00</published>
  <updated>2026-08-01T13:00:00+00:00</updated>
  <media:group>
   <media:title>First Video</media:title>
   <media:thumbnail url="https://i.ytimg.com/vi/vid1/hqdefault.jpg" width="480" height="360"/>
  </media:group>
 </entry>
 <entry>
  <id>yt:video:vid2</id>
  <yt:videoId>vid2</yt:videoId>
  <yt:channelId>UCxxxx</yt:channelId>
  <title>Second Video</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=vid2"/>
  <author><name>Example Channel</name></author>
  <published>2026-07-30T09:00:00+00:00</published>
  <updated>2026-07-30T10:00:00+00:00</updated>
  <media:group>
   <media:title>Second Video</media:title>
   <media:thumbnail url="https://i.ytimg.com/vi/vid2/hqdefault.jpg" width="480" height="360"/>
  </media:group>
 </entry>
</feed>
"""


@responses.activate
def test_fetch_channel_videos_parses_entries():
    responses.add(responses.GET, YOUTUBE_FEED_URL, body=SAMPLE_FEED, status=200)

    videos = fetch_channel_videos("UCxxxx", channel_name="Example Channel")

    assert len(videos) == 2
    first = videos[0]
    assert first.video_id == "vid1"
    assert first.title == "First Video"
    assert first.url == "https://www.youtube.com/watch?v=vid1"
    assert first.channel_name == "Example Channel"
    assert first.thumbnail_url == "https://i.ytimg.com/vi/vid1/hqdefault.jpg"
    assert first.published_at == "2026-08-01T12:00:00Z"


@responses.activate
def test_fetch_channel_videos_passes_channel_id_param():
    responses.add(responses.GET, YOUTUBE_FEED_URL, body=SAMPLE_FEED, status=200)

    fetch_channel_videos("UCxxxx")

    request = responses.calls[0].request
    assert "channel_id=UCxxxx" in request.url


@responses.activate
def test_fetch_channel_videos_falls_back_to_feed_author_name():
    responses.add(responses.GET, YOUTUBE_FEED_URL, body=SAMPLE_FEED, status=200)

    videos = fetch_channel_videos("UCxxxx")

    assert videos[0].channel_name == "Example Channel"


@responses.activate
def test_fetch_channel_videos_empty_feed_returns_empty_list():
    empty_feed = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Empty</title></feed>"""
    responses.add(responses.GET, YOUTUBE_FEED_URL, body=empty_feed, status=200)

    assert fetch_channel_videos("UCempty") == []


@responses.activate
def test_fetch_channel_videos_http_error_raises(no_sleep):
    responses.add(responses.GET, YOUTUBE_FEED_URL, status=404)

    try:
        fetch_channel_videos("UCmissing")
        assert False, "expected YouTubeError"
    except YouTubeError as exc:
        assert "404" in str(exc)


@responses.activate
def test_fetch_channel_videos_connection_error_raises(no_sleep):
    import requests

    for _ in range(4):
        responses.add(responses.GET, YOUTUBE_FEED_URL, body=requests.exceptions.ConnectionError())

    try:
        fetch_channel_videos("UCdown")
        assert False, "expected YouTubeError"
    except YouTubeError:
        pass
