"""Tests for ``forekast_mesh.message_formatter``."""

from __future__ import annotations

from datetime import date

from forekast_mesh.config import MessageConfig
from forekast_mesh.message_formatter import _utf8_safe_truncate, format_goodnight


def _cfg(**overrides) -> MessageConfig:
    base = MessageConfig(
        greeting="Goodnight mesh! Tomorrow:",
        no_events_suffix="Nothing scheduled",
        reply_hint="DM 'forekast tomorrow' for full list",
        max_events=2,
        max_event_chars=150,
        max_chars=200,
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


def test_empty_events_returns_no_events_message() -> None:
    cfg = _cfg()
    msg = format_goodnight([], date(2026, 5, 30), cfg)
    assert "Goodnight mesh! Tomorrow:" in msg
    assert "Nothing scheduled" in msg
    assert "DM 'forekast tomorrow'" in msg
    assert len(msg.encode("utf-8")) <= cfg.max_chars


def test_empty_events_with_blank_no_events_falls_back() -> None:
    cfg = _cfg(no_events_suffix="")
    msg = format_goodnight([], date(2026, 5, 30), cfg)
    assert "Nothing scheduled" in msg


def test_single_event_included_verbatim() -> None:
    cfg = _cfg()
    events = ["Solar eclipse viewing party"]
    msg = format_goodnight(events, date(2026, 5, 30), cfg)
    assert "Solar eclipse viewing party" in msg
    assert "Goodnight mesh!" in msg


def test_two_events_separated_by_period() -> None:
    cfg = _cfg()
    events = ["Solar eclipse viewing party", "Backyard cookout 6pm"]
    msg = format_goodnight(events, date(2026, 5, 30), cfg)
    assert "Solar eclipse viewing party. Backyard cookout 6pm" in msg


def test_more_events_than_max_emits_overflow_hint() -> None:
    cfg = _cfg(max_events=2)
    events = ["A", "B", "C", "D"]
    msg = format_goodnight(events, date(2026, 5, 30), cfg)
    assert "(+2 more)" in msg


def test_drops_overflow_hint_to_fit_byte_budget() -> None:
    # Force a tight budget where the (+N more) suffix would push over
    cfg = _cfg(max_chars=80, max_events=2)
    events = ["EventA", "EventB", "EventC", "EventD"]
    msg = format_goodnight(events, date(2026, 5, 30), cfg)
    assert len(msg.encode("utf-8")) <= cfg.max_chars


def test_no_reply_hint_means_no_trailing_period() -> None:
    cfg = _cfg(reply_hint="")
    msg = format_goodnight(["Just one"], date(2026, 5, 30), cfg)
    assert not msg.endswith(". ")
    assert "DM" not in msg


def test_max_chars_enforced_with_long_event() -> None:
    cfg = _cfg(max_chars=120)
    events = ["X" * 500]
    msg = format_goodnight(events, date(2026, 5, 30), cfg)
    assert len(msg.encode("utf-8")) <= cfg.max_chars
    assert "..." in msg


def test_max_chars_enforced_with_many_events() -> None:
    cfg = _cfg(max_chars=100, max_events=5)
    events = [f"Event {i} with some words" for i in range(5)]
    msg = format_goodnight(events, date(2026, 5, 30), cfg)
    assert len(msg.encode("utf-8")) <= cfg.max_chars


def test_max_event_chars_truncates_each_event() -> None:
    cfg = _cfg(max_event_chars=10, max_events=1, max_chars=200)
    events = ["this is way more than ten chars"]
    msg = format_goodnight(events, date(2026, 5, 30), cfg)
    assert "this is wa" in msg
    assert "this is way more than ten chars" not in msg


def test_utf8_safe_truncate_basic() -> None:
    assert _utf8_safe_truncate("hello", 100) == "hello"
    assert _utf8_safe_truncate("hello", 3) == "hel"


def test_utf8_safe_truncate_emoji_boundary() -> None:
    # The fire emoji is 4 bytes in UTF-8. Truncating mid-byte must not produce
    # garbage; we should walk back to a clean codepoint boundary.
    text = "abc\U0001F525def"  # \U0001F525 = fire emoji
    encoded = text.encode("utf-8")
    assert len(encoded) == 10  # 3 + 4 + 3
    # Cut at 5 (mid-emoji) — should return only "abc"
    out = _utf8_safe_truncate(text, 5)
    assert out == "abc"
    # Cut at 7 (end of emoji) — should keep emoji
    out = _utf8_safe_truncate(text, 7)
    assert out == "abc\U0001F525"


def test_imperial_metric_units_n_a_for_calendar() -> None:
    # Formatter is unit-agnostic — events are pre-formatted strings — assert
    # the formatter doesn't munge the body
    cfg = _cfg()
    events = ["Drive home (300 km)", "Pickup at 5pm (5 mi out)"]
    msg = format_goodnight(events, date(2026, 5, 30), cfg)
    assert "300 km" in msg
    assert "5 mi" in msg


def test_message_includes_period_separator_when_reply_hint_present() -> None:
    cfg = _cfg()
    msg = format_goodnight(["One"], date(2026, 5, 30), cfg)
    assert ". DM 'forekast tomorrow' for full list" in msg
