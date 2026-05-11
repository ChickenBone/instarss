from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import requests

from app.feed import fetch_feed, FeedItem

SAMPLE_ATOM = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Test Feed</title>
  <entry>
    <id>https://example.com/item-1</id>
    <title>Item One</title>
    <link href="https://example.com/item-1"/>
    <published>2024-01-15T10:00:00Z</published>
  </entry>
  <entry>
    <id>https://example.com/item-2</id>
    <title>Item Two</title>
    <link href="https://example.com/item-2"/>
  </entry>
  <entry>
    <title>No Link Entry</title>
  </entry>
</feed>"""


def _mock_response(content: bytes, status: int = 200):
    resp = requests.models.Response()
    resp.status_code = status
    resp._content = content
    return resp


def test_fetch_feed_success():
    with patch("app.feed.requests.get") as mock_get:
        mock_get.return_value = _mock_response(SAMPLE_ATOM)
        items = fetch_feed("https://example.com/feed", timeout=10)

    assert len(items) == 2
    assert items[0].title == "Item One"
    assert items[0].url == "https://example.com/item-1"
    assert items[0].guid == "https://example.com/item-1"
    assert items[1].title == "Item Two"


def test_fetch_feed_404_returns_empty():
    with patch("app.feed.requests.get") as mock_get:
        resp = _mock_response(b"", status=404)
        mock_get.return_value = resp
        resp.raise_for_status = lambda: (_ for _ in ()).throw(
            requests.exceptions.HTTPError(response=resp)
        )
        items = fetch_feed("https://example.com/feed", timeout=10)
    assert items == []


def test_fetch_feed_timeout_returns_empty():
    with patch("app.feed.requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.Timeout("timed out")
        items = fetch_feed("https://example.com/feed", timeout=10)
    assert items == []


def test_entry_without_link_skipped():
    with patch("app.feed.requests.get") as mock_get:
        mock_get.return_value = _mock_response(SAMPLE_ATOM)
        items = fetch_feed("https://example.com/feed", timeout=10)
    urls = [i.url for i in items]
    assert all(u for u in urls)
    assert len(items) == 2


def test_published_parsed_conversion():
    with patch("app.feed.requests.get") as mock_get:
        mock_get.return_value = _mock_response(SAMPLE_ATOM)
        items = fetch_feed("https://example.com/feed", timeout=10)
    assert items[0].published == datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    assert items[1].published is None
