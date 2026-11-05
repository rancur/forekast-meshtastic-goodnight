"""End-to-end calendar states: real HTTP parsing, stubbed transport, real CLI exit code."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
import requests_mock
from click.testing import CliRunner

from forekast_mesh.__main__ import cli
from forekast_mesh.config import AppConfig
from forekast_mesh.forecast_client import ForecastClient
from forekast_mesh.goodnight_poster import post_goodnight

NO_EVENTS_ICS = (
    b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//forekast-test//EN\r\nEND:VCALENDAR\r\n"
)
HTML_BODY = b"<html><body>502 Bad Gateway</body></html>"
CORRUPT_ICS = b"BEGIN:VCALENDAR\r\nthis is not ics\r\n"


def _run(cfg: AppConfig, target: date, **response: object) -> tuple:
    fc = ForecastClient(cfg)
    fc.get_tomorrow = MagicMock(return_value=target)  # type: ignore[method-assign]
    mm = MagicMock()
    mm.post_message.return_value = True
    with requests_mock.Mocker() as m:
        m.get(cfg.calendar.url, **response)
        result = post_goodnight(cfg, forecast_client=fc, meshmonitor_client=mm)
    return result, mm


@pytest.mark.parametrize(
    "response",
    [
        pytest.param({"status_code": 503, "text": "down"}, id="dead-calendar"),
        pytest.param({"status_code": 200, "content": HTML_BODY}, id="200-html"),
        pytest.param({"status_code": 200, "content": b""}, id="200-empty-body"),
        pytest.param({"status_code": 200, "content": CORRUPT_ICS}, id="200-corrupt-ics"),
    ],
)
def test_unusable_calendar_posts_nothing(
    stub_config: AppConfig, target_date: date, response: dict
) -> None:
    result, mm = _run(stub_config, target_date, **response)
    assert result.success is False
    assert result.sent is False
    assert result.message == ""
    assert result.reason
    assert mm.post_message.call_count == 0


def test_valid_calendar_with_no_events_still_posts(
    stub_config: AppConfig, target_date: date
) -> None:
    result, mm = _run(stub_config, target_date, content=NO_EVENTS_ICS)
    assert result.success is True
    assert result.sent is True
    assert "Nothing scheduled" in result.message
    assert mm.post_message.call_count == 1


def test_calendar_with_only_other_days_still_posts(
    stub_config: AppConfig, target_date: date, sample_ics_empty: bytes
) -> None:
    result, mm = _run(stub_config, target_date, content=sample_ics_empty)
    assert result.sent is True
    assert "Nothing scheduled" in result.message
    assert mm.post_message.call_count == 1


def test_happy_path_posts_events(
    stub_config: AppConfig, target_date: date, sample_ics_two_events: bytes
) -> None:
    result, mm = _run(stub_config, target_date, content=sample_ics_two_events)
    assert result.success is True
    assert result.sent is True
    assert "Solar eclipse viewing party" in result.message
    assert "Nothing scheduled" not in result.message
    assert mm.post_message.call_count == 1


@pytest.mark.parametrize(
    "response",
    [
        pytest.param({"status_code": 503, "text": "down"}, id="dead-calendar"),
        pytest.param({"status_code": 200, "content": HTML_BODY}, id="200-html"),
    ],
)
def test_cli_exits_nonzero_and_posts_nothing(tmp_path, monkeypatch, response: dict) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CALENDAR_URL", "http://calendar.test/feed.ics")
    monkeypatch.setenv("CALENDAR_MAX_ATTEMPTS", "1")
    monkeypatch.setenv("CALENDAR_RETRY_SLEEP_SECONDS", "0")
    with (
        requests_mock.Mocker() as m,
        patch("forekast_mesh.goodnight_poster.MeshMonitorClient") as mm_cls,
    ):
        m.get("http://calendar.test/feed.ics", **response)
        result = CliRunner().invoke(cli, ["post-goodnight"])
    assert result.exit_code == 1
    assert mm_cls.return_value.post_message.call_count == 0
