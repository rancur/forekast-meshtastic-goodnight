"""Glue: fetch tomorrow's events, format, and post via MeshMonitor."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .config import AppConfig
from .forecast_client import ForecastClient, ForecastFetchError
from .message_formatter import format_goodnight
from .meshmonitor_client import MeshMonitorClient

logger = logging.getLogger(__name__)


@dataclass
class PostResult:
    success: bool
    message: str
    reason: str = ""
    sent: bool = False


def post_goodnight(
    cfg: AppConfig,
    *,
    forecast_client: ForecastClient | None = None,
    meshmonitor_client: MeshMonitorClient | None = None,
    dry_run: bool = False,
) -> PostResult:
    """Build + send the nightly goodnight broadcast.

    Either client can be injected for testing. ``dry_run=True`` returns the
    formatted message but does not post.
    """
    fc = forecast_client or ForecastClient(cfg)
    mm = meshmonitor_client or MeshMonitorClient(cfg)

    tomorrow = fc.get_tomorrow()
    try:
        ics = fc.fetch_ics()
        events = fc.events_for_date(ics, tomorrow)
    except ForecastFetchError as e:
        # A dead or unusable calendar is NOT an empty calendar. Formatting []
        # here would broadcast a confident "Nothing scheduled" for a night we
        # cannot vouch for, indistinguishable from a genuinely quiet night.
        # Stay silent and let the caller fail loudly instead.
        logger.error("calendar unavailable, not posting: %s", e)
        return PostResult(success=False, message="", reason=str(e), sent=False)

    message = format_goodnight(events, tomorrow, cfg.message)
    logger.info("goodnight message: %s", message)

    if dry_run:
        return PostResult(success=True, message=message, sent=False)

    ok = mm.post_message(message, label="goodnight")
    return PostResult(success=ok, message=message, sent=ok)
