import os
import sys

import pytest
import yaml

from app.config import Config, load_or_scaffold


def test_load_valid_config(tmp_path, valid_config_dict):
    p = tmp_path / "config.yml"
    p.write_text(yaml.dump(valid_config_dict))
    cfg = load_or_scaffold(str(p))
    assert cfg.instapaper.username == "test@example.com"
    assert cfg.schedule == "*/30 * * * *"
    assert len(cfg.feeds) == 1


def test_scaffold_creates_file_and_exits(tmp_path):
    p = tmp_path / "config" / "config.yml"
    with pytest.raises(SystemExit) as exc_info:
        load_or_scaffold(str(p))
    assert exc_info.value.code == 0
    assert p.exists()


def test_scaffolded_file_is_valid_yaml(tmp_path):
    p = tmp_path / "config.yml"
    with pytest.raises(SystemExit):
        load_or_scaffold(str(p))
    content = yaml.safe_load(p.read_text())
    assert isinstance(content, dict)
    assert "instapaper" in content


def test_missing_instapaper_username_raises(tmp_path):
    bad = {"instapaper": {"password": "x"}, "schedule": "*/30 * * * *", "feeds": []}
    p = tmp_path / "config.yml"
    p.write_text(yaml.dump(bad))
    with pytest.raises(SystemExit) as exc_info:
        load_or_scaffold(str(p))
    assert exc_info.value.code == 1


def test_invalid_log_level_raises(tmp_path, valid_config_dict):
    valid_config_dict["settings"]["log_level"] = "VERBOSE"
    p = tmp_path / "config.yml"
    p.write_text(yaml.dump(valid_config_dict))
    with pytest.raises(SystemExit) as exc_info:
        load_or_scaffold(str(p))
    assert exc_info.value.code == 1


def test_invalid_crontab_raises(tmp_path, valid_config_dict):
    valid_config_dict["schedule"] = "not a cron"
    p = tmp_path / "config.yml"
    p.write_text(yaml.dump(valid_config_dict))
    with pytest.raises(SystemExit) as exc_info:
        load_or_scaffold(str(p))
    assert exc_info.value.code == 1


def test_env_override_log_level(tmp_path, valid_config_dict, monkeypatch):
    valid_config_dict["settings"]["log_level"] = "WARNING"
    p = tmp_path / "config.yml"
    p.write_text(yaml.dump(valid_config_dict))
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    cfg = load_or_scaffold(str(p))
    assert cfg.settings.log_level == "DEBUG"
