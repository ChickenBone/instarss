import os
import sys
import logging

import yaml
from pydantic import BaseModel, field_validator, model_validator
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_TEMPLATE = """\
# instarss configuration
# Edit this file, then restart the container.

instapaper:
  username: "your@email.com"
  password: "yourpassword"
  # Optional: enable auto-archive by adding OAuth credentials.
  # Register at instapaper.com/main/request_oauth_consumer_token to get these.
  # On first start with consumer_key/secret set, tokens are fetched automatically.
  # consumer_key: ""
  # consumer_secret: ""

# Cron schedule for feed polling (standard 5-field crontab syntax)
# Examples: "*/15 * * * *" = every 15 min, "0 * * * *" = hourly
schedule: "*/30 * * * *"

feeds:
  - name: "Hacker News Best"
    url: "https://hnrss.org/best"
    enabled: true
  - name: "Example Feed"
    url: "https://example.com/feed.xml"
    enabled: false

settings:
  # Max items submitted to Instapaper per feed per run (flood guard)
  max_items_per_run: 20
  # Only submit items published within this many days (0 = no cutoff)
  backfill_days: 7
  # HTTP timeout in seconds for feed fetches and Instapaper API
  request_timeout: 30
  # Log level: DEBUG, INFO, WARNING, ERROR
  log_level: "INFO"
  # Auto-archive unread items older than this many days (0 = disabled)
  # Requires consumer_key and consumer_secret above
  archive_after_days: 0
"""


class InstapaperConfig(BaseModel):
    username: str
    password: str = ""
    consumer_key: str = ""
    consumer_secret: str = ""
    access_token: str = ""
    access_token_secret: str = ""

    def archive_enabled(self) -> bool:
        return bool(self.consumer_key and self.consumer_secret)

    def has_tokens(self) -> bool:
        return bool(self.access_token and self.access_token_secret)


class FeedConfig(BaseModel):
    name: str
    url: str
    enabled: bool = True


class SettingsConfig(BaseModel):
    max_items_per_run: int = 20
    backfill_days: int = 7
    request_timeout: int = 30
    log_level: str = "INFO"
    archive_after_days: int = 0

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if v.upper() not in allowed:
            raise ValueError(f"log_level must be one of {allowed}, got: {v!r}")
        return v.upper()


class Config(BaseModel):
    instapaper: InstapaperConfig
    schedule: str = "*/30 * * * *"
    feeds: list[FeedConfig]
    settings: SettingsConfig = SettingsConfig()


def load_or_scaffold(path: str) -> tuple["Config", dict]:
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(DEFAULT_CONFIG_TEMPLATE)
        logger.warning(
            "Config scaffolded at %s — edit it with your credentials and feeds, then restart.",
            path,
        )
        sys.exit(0)

    with open(path, "r", encoding="utf-8") as f:
        try:
            raw = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            logger.critical("Failed to parse config YAML at %s: %s", path, exc)
            sys.exit(1)

    if not isinstance(raw, dict):
        logger.critical("Config at %s is not a YAML mapping.", path)
        sys.exit(1)

    try:
        config = Config.model_validate(raw)
    except Exception as exc:
        logger.critical("Config validation failed: %s", exc)
        sys.exit(1)

    try:
        CronTrigger.from_crontab(config.schedule)
    except Exception as exc:
        logger.critical("Invalid cron schedule %r: %s", config.schedule, exc)
        sys.exit(1)

    env_level = os.getenv("LOG_LEVEL", "").upper()
    if env_level and env_level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        if logging.getLevelName(env_level) < logging.getLevelName(config.settings.log_level):
            config.settings.log_level = env_level

    return config, raw


def write_tokens(path: str, raw: dict, access_token: str, access_token_secret: str) -> None:
    raw["instapaper"]["access_token"] = access_token
    raw["instapaper"]["access_token_secret"] = access_token_secret
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(raw, f, default_flow_style=False, allow_unicode=True)
    logger.info("OAuth tokens saved to %s — you can remove username/password if you like", path)
