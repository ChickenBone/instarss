import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import feedparser
import requests

logger = logging.getLogger(__name__)


@dataclass
class FeedItem:
    guid: str
    title: str
    url: str
    published: Optional[datetime]


def fetch_feed(url: str, timeout: int = 30) -> list[FeedItem]:
    try:
        response = requests.get(url, timeout=timeout, headers={"User-Agent": "instarss/1.0"})
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Failed to fetch feed %s: %s", url, exc)
        return []

    d = feedparser.parse(response.content)

    if d.bozo:
        logger.warning("Malformed feed at %s (bozo=%s) — processing available entries", url, d.bozo_exception)

    items: list[FeedItem] = []
    for entry in d.entries:
        item_url = entry.get("link")
        if not item_url:
            continue

        guid = entry.get("id") or item_url
        title = entry.get("title") or "Untitled"

        published: Optional[datetime] = None
        if entry.get("published_parsed"):
            try:
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                pass

        items.append(FeedItem(guid=guid, title=title, url=item_url, published=published))

    return items
