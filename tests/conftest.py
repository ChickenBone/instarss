import sqlite3
from unittest.mock import MagicMock

import pytest

from app.db import init_db
from app.instapaper import InstapaperClient


@pytest.fixture
def in_memory_db() -> sqlite3.Connection:
    return init_db(":memory:")


@pytest.fixture
def mock_instapaper_client() -> MagicMock:
    client = MagicMock(spec=InstapaperClient)
    client.add_url.return_value = None
    return client


@pytest.fixture
def valid_config_dict() -> dict:
    return {
        "instapaper": {"username": "test@example.com", "password": "secret"},
        "schedule": "*/30 * * * *",
        "feeds": [
            {"name": "Test Feed", "url": "https://example.com/feed.xml", "enabled": True}
        ],
        "settings": {
            "max_items_per_run": 5,
            "backfill_days": 7,
            "request_timeout": 10,
            "log_level": "INFO",
        },
    }
