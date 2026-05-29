"""Tests for ``forekast_mesh.forecast_client``."""

from __future__ import annotations

from datetime import date

import pytest
import requests_mock

from forekast_mesh.config import AppConfig
from forekast_mesh.forecast_client import ForecastClient, ForecastFetchError


def test_fetch_ics_success(stub_config: AppConfig, sample_ics_two_events: bytes) -> None:
    fc = ForecastClient(stub_config)
    with requests_mock.Mocker() as m:
        m.get(stub_config.calendar.url, content=sample_ics_two_events)
        out = fc.fetch_ics()
    assert out == sample_ics_two_events


def test_fetch_ics_empty_url_raises(minimal_config: AppConfig) -> None:
    fc = ForecastClient(minimal_config)
    with pytest.raises(ForecastFetchError) as exc:
        fc.fetch_ics()
    assert "CALENDAR_URL" in str(exc.value)


def test_fetch_ics_retries_then_succeeds(
    stub_config: AppConfig, sample_ics_two_events: bytes
) -> None:
    fc = ForecastClient(stub_config)
    with requests_mock.Mocker() as m:
        m.get(
            stub_config.calendar.url,
            [
                {"status_code": 503, "text": "down"},
                {"status_code": 200, "content": sample_ics_two_events},
            ],
        )
        out = fc.fetch_ics()
    assert out == sample_ics_two_events


def test_fetch_ics_all_attempts_fail(stub_config: AppConfig) -> None:
    fc = ForecastClient(stub_config)
    with requests_mock.Mocker() as m:
        m.get(stub_config.calendar.url, status_code=503, text="down")
        with pytest.raises(ForecastFetchError) as exc:
            fc.fetch_ics()
    assert "attempts" in str(exc.value)


def test_events_for_date_returns_matching_summaries(
    stub_config: AppConfig, sample_ics_two_events: bytes, target_date: date
) -> None:
    fc = ForecastClient(stub_config)
    out = fc.events_for_date(sample_ics_two_events, target_date)
    assert "Solar eclipse viewing party" in out
    assert "Backyard cookout 6pm" in out
    assert "Other day event" not in out


def test_events_for_date_empty_when_no_matches(
    stub_config: AppConfig, sample_ics_empty: bytes, target_date: date
) -> None:
    fc = ForecastClient(stub_config)
    out = fc.events_for_date(sample_ics_empty, target_date)
    assert out == []


def test_events_for_date_invalid_ics_returns_empty(stub_config: AppConfig) -> None:
    fc = ForecastClient(stub_config)
    out = fc.events_for_date(b"this is not ics", date(2026, 5, 30))
    assert out == []


def test_get_local_now_returns_aware_datetime(stub_config: AppConfig) -> None:
    fc = ForecastClient(stub_config)
    now = fc.get_local_now()
    assert now.tzinfo is not None


def test_get_tomorrow_is_today_plus_one(stub_config: AppConfig) -> None:
    fc = ForecastClient(stub_config)
    now = fc.get_local_now()
    tomorrow = fc.get_tomorrow()
    delta_days = (tomorrow - now.date()).days
    assert delta_days == 1


def test_unknown_timezone_falls_back_to_utc(stub_config: AppConfig) -> None:
    stub_config.timezone = "Definitely/NotARealTimezone"
    fc = ForecastClient(stub_config)
    # Should not raise — falls back to UTC
    now = fc.get_local_now()
    assert now.tzinfo is not None


def test_fallback_parser_via_static_method() -> None:
    ics = (
        b"BEGIN:VCALENDAR\r\n"
        b"BEGIN:VEVENT\r\n"
        b"DTSTART:20260530T120000Z\r\n"
        b"SUMMARY:My event\r\n"
        b"END:VEVENT\r\n"
        b"END:VCALENDAR\r\n"
    )
    out = list(ForecastClient._fallback_parse(ics, "20260530"))
    assert out == ["My event"]
