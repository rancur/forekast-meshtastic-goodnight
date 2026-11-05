"""ICS calendar client.

Fetches an ICS feed (Forekast.com, Google Calendar, self-hosted CalDAV, static
.ics) with retry and returns a date-resolved list of event summaries.

Calendar parsing uses ``icalendar`` when present and falls back to a tolerant
line parser so the package works on minimal hosts where ``icalendar`` isn't
installed.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable

import requests
from dateutil import tz as dateutil_tz

from .config import AppConfig

logger = logging.getLogger(__name__)


class ForecastFetchError(Exception):
    """Raised when the ICS feed couldn't be fetched after all retries."""


@dataclass(frozen=True)
class CalendarEvent:
    summary: str
    start: date


def _looks_like_ics(body: bytes) -> bool:
    """True if ``body`` opens like an iCalendar stream (ignoring BOM + whitespace)."""
    head = body.lstrip(b"\xef\xbb\xbf \t\r\n")[:15]
    return head.upper() == b"BEGIN:VCALENDAR"


class ForecastClient:
    """Thin client over an ICS calendar feed."""

    def __init__(self, config: AppConfig, session: requests.Session | None = None):
        self.config = config
        self.session = session or requests.Session()

    # --- fetch -------------------------------------------------------------
    def fetch_ics(self) -> bytes:
        """Fetch the configured ICS feed, retrying on transient errors."""
        url = self.config.calendar.url
        if not url:
            raise ForecastFetchError("calendar.url is empty — set CALENDAR_URL")

        last_exc: Exception | None = None
        for attempt in range(1, self.config.calendar.max_attempts + 1):
            try:
                resp = self.session.get(
                    url,
                    timeout=self.config.calendar.timeout_seconds,
                    headers={"User-Agent": "forekast-meshtastic-goodnight/0.1"},
                )
                resp.raise_for_status()
                if not _looks_like_ics(resp.content):
                    raise requests.RequestException("response body is not an ICS calendar")
                return resp.content
            except (requests.RequestException, OSError) as e:
                last_exc = e
                logger.warning(
                    "calendar fetch attempt %d/%d failed: %s",
                    attempt,
                    self.config.calendar.max_attempts,
                    e,
                )
                if attempt < self.config.calendar.max_attempts:
                    time.sleep(self.config.calendar.retry_sleep_seconds)

        raise ForecastFetchError(
            f"calendar fetch failed after {self.config.calendar.max_attempts} attempts: {last_exc}"
        )

    # --- date helpers ------------------------------------------------------
    def get_local_now(self) -> datetime:
        """Return the current wall-clock time in the configured timezone."""
        tz = dateutil_tz.gettz(self.config.timezone) or dateutil_tz.UTC
        return datetime.now(tz)

    def get_tomorrow(self) -> date:
        """Tomorrow's local date (per configured timezone)."""
        return self.get_local_now().date() + timedelta(days=1)

    # --- parse -------------------------------------------------------------
    def events_for_date(self, ics_bytes: bytes, target: date) -> list[str]:
        """Return the SUMMARY values for VEVENTs starting on ``target``."""
        target_str = target.strftime("%Y%m%d")
        try:
            from icalendar import Calendar  # type: ignore

            try:
                cal = Calendar.from_ical(ics_bytes)
            except Exception as e:
                # Unparseable is not the same as a day with no events.
                raise ForecastFetchError(f"ics parse error: {e}") from e
            return [s for s in self._walk_icalendar(cal, target_str) if s]
        except ImportError:
            return [s for s in self._fallback_parse(ics_bytes, target_str) if s]

    # --- internal ----------------------------------------------------------
    @staticmethod
    def _walk_icalendar(cal: object, target_str: str) -> Iterable[str]:
        """Yield SUMMARY values for VEVENTs that start on ``target_str`` (YYYYMMDD)."""
        # ``cal`` is icalendar.Calendar but we keep typing loose to avoid
        # importing it at module level (it's an optional dep).
        for comp in cal.walk():  # type: ignore[attr-defined]
            if comp.name != "VEVENT":
                continue
            dtstart = comp.get("dtstart")
            if not dtstart:
                continue
            d = dtstart.dt
            ds = d.strftime("%Y%m%d") if isinstance(d, (datetime, date)) else ""
            if ds == target_str:
                summary = str(comp.get("summary", "")).strip()
                if summary:
                    yield summary

    @staticmethod
    def _fallback_parse(ics_bytes: bytes, target_str: str) -> Iterable[str]:
        """Tolerant line-parser for when ``icalendar`` isn't installed."""
        in_event = False
        cur_summary = ""
        cur_dtstart = ""
        for raw in ics_bytes.decode("utf-8", errors="replace").splitlines():
            line = raw.strip()
            if line == "BEGIN:VEVENT":
                in_event = True
                cur_summary = ""
                cur_dtstart = ""
            elif line == "END:VEVENT":
                if in_event and cur_dtstart.startswith(target_str) and cur_summary:
                    yield cur_summary
                in_event = False
            elif in_event:
                if line.startswith("SUMMARY:"):
                    cur_summary = line.split(":", 1)[1].strip()
                elif line.startswith("DTSTART"):
                    cur_dtstart = line.split(":", 1)[1].strip()
