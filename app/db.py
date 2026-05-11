import sqlite3
import logging

logger = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS processed_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_url     TEXT NOT NULL,
    guid         TEXT NOT NULL,
    title        TEXT,
    item_url     TEXT,
    processed_at TEXT DEFAULT (datetime('now')),
    UNIQUE(feed_url, guid)
);
"""


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(_CREATE_TABLE)
    conn.commit()
    return conn


def is_processed(conn: sqlite3.Connection, feed_url: str, guid: str) -> bool:
    cur = conn.execute(
        "SELECT EXISTS(SELECT 1 FROM processed_items WHERE feed_url=? AND guid=?)",
        (feed_url, guid),
    )
    return bool(cur.fetchone()[0])


def mark_processed(
    conn: sqlite3.Connection,
    feed_url: str,
    guid: str,
    title: str,
    item_url: str,
) -> None:
    try:
        conn.execute(
            "INSERT OR IGNORE INTO processed_items (feed_url, guid, title, item_url) VALUES (?,?,?,?)",
            (feed_url, guid, title, item_url),
        )
        conn.commit()
    except sqlite3.Error as exc:
        logger.warning("Failed to mark item as processed (feed=%s guid=%s): %s", feed_url, guid, exc)
