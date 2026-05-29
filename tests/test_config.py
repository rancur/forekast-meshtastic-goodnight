"""Tests for ``forekast_mesh.config``."""

from __future__ import annotations

import os
from unittest.mock import patch

from forekast_mesh.config import AppConfig, load_config


def test_minimal_defaults() -> None:
    cfg = AppConfig()
    assert cfg.calendar.url == ""
    assert cfg.calendar.timeout_seconds == 15
    assert cfg.calendar.max_attempts == 3
    assert cfg.meshmonitor.url == "http://localhost:8080"
    assert cfg.meshmonitor.channel_index == 0
    assert cfg.message.max_chars == 200
    assert cfg.message.max_events == 2
    assert cfg.timezone == "America/Phoenix"
    assert cfg.logging.level == "INFO"


def test_load_no_yaml_no_env(tmp_path) -> None:
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        with patch.dict(os.environ, {}, clear=True):
            cfg = load_config()
        assert cfg.calendar.url == ""
        assert cfg.meshmonitor.api_token == ""
    finally:
        os.chdir(cwd)


def test_load_yaml_basic(write_config_yaml) -> None:
    p = write_config_yaml(
        """
calendar:
  url: "http://example.com/cal.ics"
  timeout_seconds: 30
meshmonitor:
  url: "http://mm.example.com:9090"
  api_token: "abc"
  channel_index: 2
message:
  greeting: "Night night!"
  max_chars: 180
timezone: "America/Los_Angeles"
"""
    )
    with patch.dict(os.environ, {}, clear=True):
        cfg = load_config(p)
    assert cfg.calendar.url == "http://example.com/cal.ics"
    assert cfg.calendar.timeout_seconds == 30
    assert cfg.meshmonitor.url == "http://mm.example.com:9090"
    assert cfg.meshmonitor.api_token == "abc"
    assert cfg.meshmonitor.channel_index == 2
    assert cfg.message.greeting == "Night night!"
    assert cfg.message.max_chars == 180
    assert cfg.timezone == "America/Los_Angeles"


def test_env_overrides_yaml(write_config_yaml) -> None:
    p = write_config_yaml(
        """
calendar:
  url: "http://from-yaml.test/cal.ics"
meshmonitor:
  api_token: "yaml-token"
  channel_index: 0
"""
    )
    env = {
        "CALENDAR_URL": "http://from-env.test/cal.ics",
        "MESHMONITOR_API_TOKEN": "env-token",
        "MESHMONITOR_CHANNEL_INDEX": "3",
        "MESSAGE_MAX_CHARS": "150",
        "GOODNIGHT_TZ": "Europe/London",
    }
    with patch.dict(os.environ, env, clear=True):
        cfg = load_config(p)
    assert cfg.calendar.url == "http://from-env.test/cal.ics"
    assert cfg.meshmonitor.api_token == "env-token"
    assert cfg.meshmonitor.channel_index == 3
    assert cfg.message.max_chars == 150
    assert cfg.timezone == "Europe/London"


def test_yaml_env_interpolation(write_config_yaml) -> None:
    p = write_config_yaml(
        """
calendar:
  url: "${MY_CAL_URL}"
meshmonitor:
  api_token: "${MY_MM_TOKEN}"
"""
    )
    env = {"MY_CAL_URL": "http://interp.test/cal.ics", "MY_MM_TOKEN": "interp-token"}
    with patch.dict(os.environ, env, clear=True):
        cfg = load_config(p)
    assert cfg.calendar.url == "http://interp.test/cal.ics"
    assert cfg.meshmonitor.api_token == "interp-token"


def test_yaml_env_interpolation_missing_var_yields_empty(write_config_yaml) -> None:
    p = write_config_yaml(
        """
calendar:
  url: "${NOT_SET_VAR}"
"""
    )
    with patch.dict(os.environ, {}, clear=True):
        cfg = load_config(p)
    assert cfg.calendar.url == ""


def test_extra_keys_rejected(write_config_yaml) -> None:
    p = write_config_yaml(
        """
calendar:
  url: "http://x.test"
bogus_top_level: "nope"
"""
    )
    with patch.dict(os.environ, {}, clear=True):
        try:
            load_config(p)
        except Exception as e:
            assert "bogus_top_level" in str(e) or "Extra" in str(e) or "extra" in str(e)
            return
        raise AssertionError("expected extra-key rejection")
