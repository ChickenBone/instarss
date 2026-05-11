import logging

import requests
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class InstapaperAuthError(Exception):
    pass


class InstapaperAPIError(Exception):
    pass


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
        return True
    if isinstance(exc, requests.exceptions.HTTPError):
        status = exc.response.status_code if exc.response is not None else None
        return status in _RETRYABLE_STATUS
    return False


class InstapaperClient:
    _API_URL = "https://www.instapaper.com/api/add"

    def __init__(self, username: str, password: str):
        self._session = requests.Session()
        self._session.auth = (username, password)

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5),
        retry=retry_if_exception(_is_retryable),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def add_url(self, url: str, title: str = "", timeout: int = 30) -> None:
        data = {"url": url}
        if title:
            data["title"] = title

        response = self._session.post(self._API_URL, data=data, timeout=timeout)

        if response.status_code == 403:
            raise InstapaperAuthError("Instapaper returned 403 — check credentials")
        if response.status_code in (200, 201):
            return
        if response.status_code >= 400:
            response.raise_for_status()
