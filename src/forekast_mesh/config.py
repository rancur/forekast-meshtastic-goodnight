"""Configuration schema + loader for forekast-meshtastic-goodnight.

Loads from a YAML file, then overlays environment variables. Pydantic validates
the shape and surfaces actionable error messages on missing / wrong-typed fields.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _expand_env(value: object) -> object:
    """Recursively replace ${VAR} occurrences in strings with os.environ values."""
    if isinstance(value, str):

        def repl(match: re.Match[str]) -> str:
            return os.environ.get(match.group(1), "")

        return _ENV_VAR_PATTERN.sub(repl, value)
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    return value


class CalendarConfig(BaseModel):
    url: str = ""
    timeout_seconds: int = 15
    max_attempts: int = 3
    retry_sleep_seconds: int = 10


class MeshMonitorConfig(BaseModel):
    url: str = "http://localhost:8080"
    api_token: str = ""
    channel_index: int = 0
    retry_max_attempts: int = 3
    retry_sleep_seconds: int = 30
    retry_timeout_seconds: int = 15


class MessageConfig(BaseModel):
    greeting: str = "Goodnight mesh! Tomorrow:"
    no_events_suffix: str = "Nothing scheduled"
    reply_hint: str = ""
    max_events: int = 2
    max_event_chars: int = 150
    max_chars: int = 200


class LoggingConfig(BaseModel):
    level: str = "INFO"


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    calendar: CalendarConfig = Field(default_factory=CalendarConfig)
    meshmonitor: MeshMonitorConfig = Field(default_factory=MeshMonitorConfig)
    message: MessageConfig = Field(default_factory=MessageConfig)
    timezone: str = "America/Phoenix"
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def _apply_env_overrides(cfg: AppConfig) -> AppConfig:
    """Environment variables override YAML so ops can rotate tokens without editing files."""
    env = os.environ

    # Calendar
    if "CALENDAR_URL" in env:
        cfg.calendar.url = env["CALENDAR_URL"]
    if "CALENDAR_TIMEOUT_SECONDS" in env:
        cfg.calendar.timeout_seconds = int(env["CALENDAR_TIMEOUT_SECONDS"])
    if "CALENDAR_MAX_ATTEMPTS" in env:
        cfg.calendar.max_attempts = int(env["CALENDAR_MAX_ATTEMPTS"])
    if "CALENDAR_RETRY_SLEEP_SECONDS" in env:
        cfg.calendar.retry_sleep_seconds = int(env["CALENDAR_RETRY_SLEEP_SECONDS"])

    # MeshMonitor
    if "MESHMONITOR_URL" in env:
        cfg.meshmonitor.url = env["MESHMONITOR_URL"]
    if "MESHMONITOR_API_TOKEN" in env:
        cfg.meshmonitor.api_token = env["MESHMONITOR_API_TOKEN"]
    if "MESHMONITOR_CHANNEL_INDEX" in env:
        cfg.meshmonitor.channel_index = int(env["MESHMONITOR_CHANNEL_INDEX"])
    if "MESHMONITOR_RETRY_MAX_ATTEMPTS" in env:
        cfg.meshmonitor.retry_max_attempts = int(env["MESHMONITOR_RETRY_MAX_ATTEMPTS"])
    if "MESHMONITOR_RETRY_SLEEP_SECONDS" in env:
        cfg.meshmonitor.retry_sleep_seconds = int(env["MESHMONITOR_RETRY_SLEEP_SECONDS"])
    if "MESHMONITOR_RETRY_TIMEOUT_SECONDS" in env:
        cfg.meshmonitor.retry_timeout_seconds = int(env["MESHMONITOR_RETRY_TIMEOUT_SECONDS"])

    # Message
    if "MESSAGE_GREETING" in env:
        cfg.message.greeting = env["MESSAGE_GREETING"]
    if "MESSAGE_NO_EVENTS_SUFFIX" in env:
        cfg.message.no_events_suffix = env["MESSAGE_NO_EVENTS_SUFFIX"]
    if "MESSAGE_REPLY_HINT" in env:
        cfg.message.reply_hint = env["MESSAGE_REPLY_HINT"]
    if "MESSAGE_MAX_EVENTS" in env:
        cfg.message.max_events = int(env["MESSAGE_MAX_EVENTS"])
    if "MESSAGE_MAX_EVENT_CHARS" in env:
        cfg.message.max_event_chars = int(env["MESSAGE_MAX_EVENT_CHARS"])
    if "MESSAGE_MAX_CHARS" in env:
        cfg.message.max_chars = int(env["MESSAGE_MAX_CHARS"])

    # Timezone
    if "GOODNIGHT_TZ" in env:
        cfg.timezone = env["GOODNIGHT_TZ"]
    elif "TZ" in env and not cfg.timezone:
        # Honor the container-standard TZ var as a fallback only.
        cfg.timezone = env["TZ"]

    if "FOREKAST_MESH_LOG_LEVEL" in env:
        cfg.logging.level = env["FOREKAST_MESH_LOG_LEVEL"]

    return cfg


def load_config(path: str | Path | None = None) -> AppConfig:
    """Load + validate config from yaml + env overlay.

    If ``path`` is None and ``config.yaml`` does not exist, returns defaults +
    env overlay only — useful for env-only deployments (Docker, Heroku-style).
    """
    raw: dict = {}
    if path is None:
        for candidate in ("config.yaml", "config.yml"):
            if Path(candidate).is_file():
                path = candidate
                break
    if path is not None and Path(path).is_file():
        with open(path) as f:
            loaded = yaml.safe_load(f) or {}
        raw = _expand_env(loaded)  # type: ignore[assignment]

    cfg = AppConfig(**raw)
    return _apply_env_overrides(cfg)
