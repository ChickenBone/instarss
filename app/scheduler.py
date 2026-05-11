import logging
import sqlite3
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import Config, FeedConfig, SettingsConfig
from .instapaper import InstapaperClient, InstapaperAuthError
from .archive import InstapaperArchiver
from . import feed as feed_module
from . import db as db_module

logger = logging.getLogger(__name__)


def build_scheduler(config: Config, db_conn: sqlite3.Connection) -> BlockingScheduler:
    client = InstapaperClient(config.instapaper.username, config.instapaper.password)
    archiver = InstapaperArchiver(config) if config.instapaper.archive_enabled() else None

    scheduler = BlockingScheduler()
    scheduler.add_job(
        _run_job,
        trigger=CronTrigger.from_crontab(config.schedule),
        args=[config, db_conn, client, archiver],
        max_instances=1,
        misfire_grace_time=300,
    )
    return scheduler


def _run_job(config: Config, db_conn: sqlite3.Connection, client: InstapaperClient, archiver) -> None:
    enabled = [f for f in config.feeds if f.enabled]
    logger.info("Running feed job — %d feed(s) enabled", len(enabled))

    for feed in enabled:
        try:
            _process_single_feed(feed, db_conn, client, config.settings)
        except Exception as exc:
            logger.error("Feed [%s] failed: %s", feed.name, exc)

    if archiver:
        archiver.run(config.settings.archive_after_days)


def _process_single_feed(
    feed: FeedConfig,
    db_conn: sqlite3.Connection,
    client: InstapaperClient,
    settings: SettingsConfig,
) -> None:
    items = feed_module.fetch_feed(feed.url, timeout=settings.request_timeout)
    if not items:
        logger.info("Feed [%s]: no items retrieved", feed.name)
        return

    cutoff = None
    if settings.backfill_days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.backfill_days)

    submitted = 0
    already_seen = 0

    for item in items:
        if submitted >= settings.max_items_per_run:
            break
        if db_module.is_processed(db_conn, feed.url, item.guid):
            already_seen += 1
            continue
        if cutoff and item.published and item.published < cutoff:
            db_module.mark_processed(db_conn, feed.url, item.guid, item.title, item.url)
            already_seen += 1
            continue
        try:
            client.add_url(item.url, title=item.title, timeout=settings.request_timeout)
            db_module.mark_processed(db_conn, feed.url, item.guid, item.title, item.url)
            submitted += 1
            logger.info("Submitted [%s] %s", feed.name, item.title[:80])
        except InstapaperAuthError:
            logger.critical("Instapaper auth error — check username/password in config")
            raise
        except Exception as exc:
            logger.error("Failed to submit item %s from [%s]: %s", item.url, feed.name, exc)

    logger.info("Feed [%s]: %d submitted, %d already seen", feed.name, submitted, already_seen)
