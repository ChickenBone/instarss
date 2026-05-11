import logging
import os
import signal
import sqlite3
import sys

from . import config as config_module
from . import db as db_module
from . import scheduler as scheduler_module

logger = logging.getLogger(__name__)


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def main() -> None:
    _configure_logging("INFO")

    config_path = os.getenv("CONFIG_PATH", "/app/config/config.yml")
    db_path = os.getenv("DB_PATH", "/app/data/instarss.db")

    cfg = config_module.load_or_scaffold(config_path)

    _configure_logging(cfg.settings.log_level)

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db_conn = db_module.init_db(db_path)

    scheduler = scheduler_module.build_scheduler(cfg, db_conn)

    enabled_count = sum(1 for f in cfg.feeds if f.enabled)
    logger.info(
        "instarss starting — schedule: %s | feeds: %d enabled | db: %s",
        cfg.schedule,
        enabled_count,
        db_path,
    )

    def _shutdown(signum: int, frame: object) -> None:
        logger.info("Shutdown signal received, stopping scheduler…")
        scheduler.shutdown(wait=False)
        db_conn.close()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        db_conn.close()


if __name__ == "__main__":
    main()
