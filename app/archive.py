import logging
import time
from urllib.parse import parse_qs

import requests
from requests_oauthlib import OAuth1Session
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from .config import Config, write_tokens

logger = logging.getLogger(__name__)

_BASE = "https://www.instapaper.com/api/1"
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
        return True
    if isinstance(exc, requests.exceptions.HTTPError):
        status = exc.response.status_code if exc.response is not None else None
        return status in _RETRYABLE_STATUS
    return False


def bootstrap_tokens(config: Config, raw: dict, config_path: str) -> None:
    """Fetch OAuth tokens via xAuth and persist them to config.yml."""
    logger.info("No OAuth tokens found — bootstrapping via xAuth...")
    oauth = OAuth1Session(
        client_key=config.instapaper.consumer_key,
        client_secret=config.instapaper.consumer_secret,
        signature_type="AUTH_HEADER",
    )
    resp = oauth.post(
        f"{_BASE}/oauth/access_token",
        data={
            "x_auth_username": config.instapaper.username,
            "x_auth_password": config.instapaper.password,
            "x_auth_mode": "client_auth",
        },
        timeout=config.settings.request_timeout,
    )
    resp.raise_for_status()
    tokens = parse_qs(resp.text)
    access_token = tokens["oauth_token"][0]
    access_token_secret = tokens["oauth_token_secret"][0]

    config.instapaper.access_token = access_token
    config.instapaper.access_token_secret = access_token_secret
    write_tokens(config_path, raw, access_token, access_token_secret)


class InstapaperArchiver:
    def __init__(self, config: Config):
        self._timeout = config.settings.request_timeout
        self._session = OAuth1Session(
            client_key=config.instapaper.consumer_key,
            client_secret=config.instapaper.consumer_secret,
            resource_owner_key=config.instapaper.access_token,
            resource_owner_secret=config.instapaper.access_token_secret,
            signature_type="AUTH_HEADER",
        )

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5),
        retry=retry_if_exception(_is_retryable),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _list_bookmarks(self, limit: int = 500) -> list[dict]:
        resp = self._session.post(
            f"{_BASE}/bookmarks/list",
            data={"limit": limit, "folder_id": "unread"},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return [item for item in resp.json() if item.get("type") == "bookmark"]

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5),
        retry=retry_if_exception(_is_retryable),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _archive(self, bookmark_id: int) -> None:
        resp = self._session.post(
            f"{_BASE}/bookmarks/archive",
            data={"bookmark_id": bookmark_id},
            timeout=self._timeout,
        )
        resp.raise_for_status()

    def run(self, archive_after_days: int) -> None:
        if archive_after_days <= 0:
            return
        cutoff = time.time() - (archive_after_days * 86400)
        try:
            bookmarks = self._list_bookmarks()
        except Exception as exc:
            logger.error("Failed to list Instapaper bookmarks: %s", exc)
            return

        archived = 0
        for bm in bookmarks:
            if bm.get("time", 0) < cutoff:
                try:
                    self._archive(bm["bookmark_id"])
                    archived += 1
                    logger.info("Archived: %s", bm.get("title", bm["bookmark_id"])[:80])
                except Exception as exc:
                    logger.error("Failed to archive bookmark %s: %s", bm["bookmark_id"], exc)

        logger.info("Archive job: %d archived, %d unread checked", archived, len(bookmarks))
