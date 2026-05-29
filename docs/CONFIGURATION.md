# Configuration

Every knob lives in `config.yaml` (gitignored) with an env-var override layer on top. `config.example.yaml` and `.env.example` ship in the repo.

Environment variables always win over YAML — rotate tokens without editing files.

## `calendar` — the ICS feed

| Field | Env | Default | Notes |
|---|---|---|---|
| `url` | `CALENDAR_URL` | _(empty)_ | Required. Public ICS URL. Forekast format: `https://forekast.com/<handle>/calendar.ics` |
| `timeout_seconds` | `CALENDAR_TIMEOUT_SECONDS` | `15` | Per-request HTTP timeout. |
| `max_attempts` | `CALENDAR_MAX_ATTEMPTS` | `3` | Retry count on transient failure. |
| `retry_sleep_seconds` | `CALENDAR_RETRY_SLEEP_SECONDS` | `10` | Sleep between retries. |

Calendar sources that work out of the box:

- **Forekast.com** — profile page → "Subscribe" → `<handle>/calendar.ics`
- **Google Calendar** — Calendar settings → "Secret address in iCal format"
- **CalDAV servers** (Radicale, Baikal, Nextcloud) — public `.ics` export
- **Static `.ics` files** behind any HTTP server

## `meshmonitor` — the broadcast target

| Field | Env | Default |
|---|---|---|
| `url` | `MESHMONITOR_URL` | `http://localhost:8080` |
| `api_token` | `MESHMONITOR_API_TOKEN` | _(empty)_ — required |
| `channel_index` | `MESHMONITOR_CHANNEL_INDEX` | `0` (primary) |
| `retry_max_attempts` | `MESHMONITOR_RETRY_MAX_ATTEMPTS` | `3` |
| `retry_sleep_seconds` | `MESHMONITOR_RETRY_SLEEP_SECONDS` | `30` |
| `retry_timeout_seconds` | `MESHMONITOR_RETRY_TIMEOUT_SECONDS` | `15` |

`MeshMonitor` abstracts storage — Postgres-backed installs (typical for fixed home / production rigs) and SQLite-backed installs (typical for mobile / RV / single-Pi rigs) speak the same `POST /api/v1/messages` shape. No backend-specific config in this package.

## `message` — the format

| Field | Env | Default |
|---|---|---|
| `greeting` | `MESSAGE_GREETING` | `Goodnight mesh! Tomorrow:` |
| `no_events_suffix` | `MESSAGE_NO_EVENTS_SUFFIX` | `Nothing scheduled` |
| `reply_hint` | `MESSAGE_REPLY_HINT` | `` (set in `.env.example` to `DM 'forekast tomorrow' for full list`) |
| `max_events` | `MESSAGE_MAX_EVENTS` | `2` |
| `max_event_chars` | `MESSAGE_MAX_EVENT_CHARS` | `150` |
| `max_chars` | `MESSAGE_MAX_CHARS` | `200` |

The formatter is UTF-8-byte-aware — it will truncate cleanly at codepoint boundaries (no half-emoji). Overflow past `max_events` is summarized as `(+N more)`.

## `timezone`

| Field | Env | Default |
|---|---|---|
| `timezone` | `GOODNIGHT_TZ` (or `TZ` as fallback) | `America/Phoenix` |

"Tomorrow" is resolved in this timezone. Forekast events are local-day, so a UTC host without this set would broadcast the wrong day at the wrong time.

## `logging`

| Field | Env | Default |
|---|---|---|
| `level` | `FOREKAST_MESH_LOG_LEVEL` | `INFO` |

## Companion: DM auto-responder

`reply_hint` advertises a DM trigger like `DM 'forekast tomorrow' for full list`. If you run **MeshMonitor**, you can hook a DM auto-responder that runs a small Python script returning the same calendar data for any date:

1. Drop a tiny script (under 70 lines — see `forecast_client.py` in this repo for the ICS parsing logic) into MeshMonitor's data dir as `forekast_query.py`.
2. In MeshMonitor: **Settings → Automation → Auto Responder → Add Trigger**.
3. Trigger pattern: `forekast (?P<date>.*)` (case-insensitive), response type: **Script**, path: `/data/scripts/forekast_query.py`.

That way the nightly broadcast advertises "tomorrow" and individual mesh users can pull "today / this Saturday / 2026-06-15" on demand.

If you don't want that, clear `reply_hint`.
