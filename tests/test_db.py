from app.db import init_db, is_processed, mark_processed


def test_init_creates_table(in_memory_db):
    cur = in_memory_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='processed_items'"
    )
    assert cur.fetchone() is not None


def test_is_processed_false_initially(in_memory_db):
    assert not is_processed(in_memory_db, "https://example.com/feed", "guid-1")


def test_mark_then_is_processed(in_memory_db):
    mark_processed(in_memory_db, "https://example.com/feed", "guid-1", "Title", "https://example.com/item1")
    assert is_processed(in_memory_db, "https://example.com/feed", "guid-1")


def test_mark_idempotent(in_memory_db):
    mark_processed(in_memory_db, "https://example.com/feed", "guid-1", "Title", "https://example.com/item1")
    mark_processed(in_memory_db, "https://example.com/feed", "guid-1", "Title", "https://example.com/item1")
    cur = in_memory_db.execute(
        "SELECT COUNT(*) FROM processed_items WHERE feed_url=? AND guid=?",
        ("https://example.com/feed", "guid-1"),
    )
    assert cur.fetchone()[0] == 1


def test_different_feeds_same_guid(in_memory_db):
    mark_processed(in_memory_db, "https://feed-a.com/rss", "guid-x", "A", "https://a.com")
    assert not is_processed(in_memory_db, "https://feed-b.com/rss", "guid-x")
