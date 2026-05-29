"""Shared pytest fixtures."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from forekast_mesh.config import AppConfig


@pytest.fixture
def minimal_config() -> AppConfig:
    """Fully-defaulted config; tweak attrs in individual tests."""
    return AppConfig()


@pytest.fixture
def stub_config() -> AppConfig:
    """Config wired to a stub calendar URL + stub MeshMonitor."""
    cfg = AppConfig()
    cfg.calendar.url = "http://calendar.test/feed.ics"
    cfg.calendar.retry_sleep_seconds = 0  # no test delays
    cfg.calendar.max_attempts = 2
    cfg.meshmonitor.url = "http://meshmonitor.test"
    cfg.meshmonitor.api_token = "mm-test-token"
    cfg.meshmonitor.channel_index = 0
    cfg.meshmonitor.retry_sleep_seconds = 0
    cfg.meshmonitor.retry_max_attempts = 2
    cfg.message.greeting = "Goodnight mesh! Tomorrow:"
    cfg.message.reply_hint = "DM 'forekast tomorrow' for full list"
    cfg.message.max_chars = 200
    cfg.message.max_events = 2
    cfg.message.max_event_chars = 150
    cfg.timezone = "America/Phoenix"
    return cfg


@pytest.fixture
def sample_ics_two_events() -> bytes:
    """A minimal ICS payload with two VEVENTs on 2026-05-30."""
    return (
        b"BEGIN:VCALENDAR\r\n"
        b"VERSION:2.0\r\n"
        b"PRODID:-//forekast-test//EN\r\n"
        b"BEGIN:VEVENT\r\n"
        b"UID:evt-1@test\r\n"
        b"DTSTART;VALUE=DATE:20260530\r\n"
        b"SUMMARY:Solar eclipse viewing party\r\n"
        b"END:VEVENT\r\n"
        b"BEGIN:VEVENT\r\n"
        b"UID:evt-2@test\r\n"
        b"DTSTART;VALUE=DATE:20260530\r\n"
        b"SUMMARY:Backyard cookout 6pm\r\n"
        b"END:VEVENT\r\n"
        b"BEGIN:VEVENT\r\n"
        b"UID:evt-3@test\r\n"
        b"DTSTART;VALUE=DATE:20260531\r\n"
        b"SUMMARY:Other day event\r\n"
        b"END:VEVENT\r\n"
        b"END:VCALENDAR\r\n"
    )


@pytest.fixture
def sample_ics_empty() -> bytes:
    """Calendar with no events on the target date."""
    return (
        b"BEGIN:VCALENDAR\r\n"
        b"VERSION:2.0\r\n"
        b"PRODID:-//forekast-test//EN\r\n"
        b"BEGIN:VEVENT\r\n"
        b"UID:other@test\r\n"
        b"DTSTART;VALUE=DATE:20260101\r\n"
        b"SUMMARY:Way in the past\r\n"
        b"END:VEVENT\r\n"
        b"END:VCALENDAR\r\n"
    )


@pytest.fixture
def target_date() -> date:
    return date(2026, 5, 30)


@pytest.fixture
def write_config_yaml(tmp_path: Path):
    def _write(body: str) -> Path:
        p = tmp_path / "config.yaml"
        p.write_text(body)
        return p

    return _write
