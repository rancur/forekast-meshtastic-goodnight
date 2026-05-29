"""Format a goodnight + tomorrow's events message for Meshtastic.

Constraints:

- ≤ ``max_chars`` bytes (Meshtastic packet limit; default 200).
- Single line.
- UTF-8-safe truncation that never emits a half-emoji.
"""

from __future__ import annotations

from datetime import date

from .config import MessageConfig


def _utf8_safe_truncate(text: str, max_bytes: int) -> str:
    """Truncate text so the encoded UTF-8 byte length ≤ ``max_bytes``.

    Walks back to the nearest codepoint boundary so we never emit a half-emoji
    or a dangling continuation byte.
    """
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    truncated = encoded[:max_bytes]
    # Try to decode; if that fails we sliced mid-codepoint. Walk back one byte
    # at a time until decodable. Bounded by max_bytes so this is O(<=4) in
    # practice (UTF-8 codepoints are at most 4 bytes).
    for cut in range(len(truncated), 0, -1):
        try:
            return truncated[:cut].decode("utf-8")
        except UnicodeDecodeError:
            continue
    return ""


def format_goodnight(
    events: list[str],
    target_date: date,
    config: MessageConfig,
) -> str:
    """Build the broadcast string for ``target_date``'s events."""
    greeting = config.greeting.strip()
    reply_hint = config.reply_hint.strip()
    suffix = f". {reply_hint}" if reply_hint else ""

    if not events:
        body = config.no_events_suffix.strip() or "Nothing scheduled"
        message = f"{greeting} {body}{suffix}"
        return _utf8_safe_truncate(message, config.max_chars)

    display = events[: max(1, config.max_events)]
    trimmed = [e[: max(1, config.max_event_chars)] for e in display]
    event_text = ". ".join(trimmed)

    # If we dropped events, append a (+N more) hint when there's room.
    dropped = len(events) - len(display)
    more_hint = f" (+{dropped} more)" if dropped > 0 else ""

    prefix = f"{greeting} "
    message = f"{prefix}{event_text}{more_hint}{suffix}"
    if len(message.encode("utf-8")) <= config.max_chars:
        return message

    # Tighten progressively until we fit the byte budget.
    # 1) Drop "(+N more)" if present
    if more_hint:
        message = f"{prefix}{event_text}{suffix}"
        if len(message.encode("utf-8")) <= config.max_chars:
            return message

    # 2) Truncate the event-list region only (keep greeting + suffix intact)
    overhead = len(prefix.encode("utf-8")) + len(suffix.encode("utf-8")) + len("...".encode("utf-8"))
    available = max(0, config.max_chars - overhead)
    trimmed_text = _utf8_safe_truncate(event_text, available)
    if trimmed_text != event_text:
        trimmed_text = trimmed_text + "..."
    message = f"{prefix}{trimmed_text}{suffix}"
    return _utf8_safe_truncate(message, config.max_chars)
