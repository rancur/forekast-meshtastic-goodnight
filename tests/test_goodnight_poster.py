"""Tests for ``forekast_mesh.goodnight_poster``."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from forekast_mesh.config import AppConfig
from forekast_mesh.forecast_client import ForecastFetchError
from forekast_mesh.goodnight_poster import post_goodnight


def _stub_forecast_client(events: list[str], target: date) -> MagicMock:
    fc = MagicMock()
    fc.get_tomorrow.return_value = target
    fc.fetch_ics.return_value = b"ICS"
    fc.events_for_date.return_value = events
    return fc


def test_post_goodnight_success(
    stub_config: AppConfig, target_date: date
) -> None:
    fc = _stub_forecast_client(["Event A", "Event B"], target_date)
    mm = MagicMock()
    mm.post_message.return_value = True

    result = post_goodnight(stub_config, forecast_client=fc, meshmonitor_client=mm)
    assert result.success is True
    assert result.sent is True
    assert "Event A" in result.message
    assert "Event B" in result.message
    assert mm.post_message.call_count == 1


def test_post_goodnight_dry_run_does_not_send(
    stub_config: AppConfig, target_date: date
) -> None:
    fc = _stub_forecast_client(["Only one"], target_date)
    mm = MagicMock()

    result = post_goodnight(
        stub_config, forecast_client=fc, meshmonitor_client=mm, dry_run=True
    )
    assert result.success is True
    assert result.sent is False
    assert mm.post_message.call_count == 0


def test_post_goodnight_no_events_still_broadcasts(
    stub_config: AppConfig, target_date: date
) -> None:
    fc = _stub_forecast_client([], target_date)
    mm = MagicMock()
    mm.post_message.return_value = True

    result = post_goodnight(stub_config, forecast_client=fc, meshmonitor_client=mm)
    assert result.success is True
    assert "Nothing scheduled" in result.message
    assert mm.post_message.call_count == 1


def test_post_goodnight_calendar_failure_still_broadcasts(
    stub_config: AppConfig, target_date: date
) -> None:
    """Calendar offline shouldn't silence the mesh — degrade to no-events."""
    fc = MagicMock()
    fc.get_tomorrow.return_value = target_date
    fc.fetch_ics.side_effect = ForecastFetchError("timeout")
    mm = MagicMock()
    mm.post_message.return_value = True

    result = post_goodnight(stub_config, forecast_client=fc, meshmonitor_client=mm)
    assert result.success is True
    assert result.reason == "timeout"
    assert mm.post_message.call_count == 1


def test_post_goodnight_calendar_failure_in_dry_run_does_not_send(
    stub_config: AppConfig, target_date: date
) -> None:
    fc = MagicMock()
    fc.get_tomorrow.return_value = target_date
    fc.fetch_ics.side_effect = ForecastFetchError("timeout")
    mm = MagicMock()

    result = post_goodnight(
        stub_config, forecast_client=fc, meshmonitor_client=mm, dry_run=True
    )
    assert result.success is False
    assert result.reason == "timeout"
    assert mm.post_message.call_count == 0


def test_post_goodnight_meshmonitor_failure_returns_unsuccessful(
    stub_config: AppConfig, target_date: date
) -> None:
    fc = _stub_forecast_client(["Event A"], target_date)
    mm = MagicMock()
    mm.post_message.return_value = False

    result = post_goodnight(stub_config, forecast_client=fc, meshmonitor_client=mm)
    assert result.success is False
    assert result.sent is False
    assert "Event A" in result.message
