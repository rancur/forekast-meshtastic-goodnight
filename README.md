# forekast-meshtastic-goodnight

[![CI](https://github.com/rancur/forekast-meshtastic-goodnight/actions/workflows/ci.yml/badge.svg)](https://github.com/rancur/forekast-meshtastic-goodnight/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

> Nightly "goodnight + tomorrow's events" broadcast for your Meshtastic mesh — reads any public ICS calendar (Forekast, Google Calendar, CalDAV) and posts a single 200-byte message via MeshMonitor.

```
Goodnight mesh! Tomorrow: Solar eclipse viewing party. Backyard cookout 6pm. DM 'forekast tomorrow' for full list
```

```
Goodnight mesh! Tomorrow: Nothing scheduled. DM 'forekast tomorrow' for full list
```

```
Goodnight mesh! Tomorrow: Rivian road-trip leg — Moab → Telluride (7am depart). DM 'forekast tomorrow' for full list
```

This is a tiny, hermetic, well-tested package that turns a public ICS calendar feed into a once-a-night Meshtastic broadcast. Designed to live next to [MeshMonitor](https://github.com/Yeraze/meshmonitor) on a Pi base station or a mobile rig.

Battle-tested as a production companion on a fixed home Meshtastic base.

---

## Why

A Meshtastic mesh is a community-of-presence radio. Your community probably wants to know what's happening tomorrow without opening an app:

- **Community heads-up** — community events, club nights, weekend convoys all surface on the mesh.
- **Personal touch** — pair with your own [Forekast.com](https://forekast.com/) profile and the mesh sees what you've publicly committed to.
- **Off-grid friendly** — runs as a single cron tick. As long as the host has internet (Starlink, RV hotspot, etc.) the mesh gets its nightly update.

It pairs naturally with a DM auto-responder (see [docs/CONFIGURATION.md](docs/CONFIGURATION.md#companion-dm-auto-responder)) so the nightly message advertises "tomorrow" and individuals can DM `forekast saturday` for any other date.

---

## What you need

- **A public ICS calendar URL.** Forekast format is `https://forekast.com/<your-handle>/calendar.ics`. Any ICS works — Google Calendar "secret iCal" links, self-hosted CalDAV, static `.ics` behind nginx.
- **A MeshMonitor instance** — https://github.com/Yeraze/meshmonitor — with `MM_API_TOKEN` set, reachable from the install host.
- **Python 3.10+**

Backend choice (Postgres vs SQLite) is invisible to this package — MeshMonitor abstracts it. Whichever you've picked, this works.

---

## Quick install

```bash
git clone https://github.com/rancur/forekast-meshtastic-goodnight.git
cd forekast-meshtastic-goodnight
./scripts/install.sh
```

The installer:

1. Builds a `.venv`, installs the package, registers the `forekast-mesh` CLI.
2. Prompts for the bare minimum: ICS URL, MeshMonitor URL + token, timezone.
3. Runs `forekast-mesh doctor` to verify both sides reachable + posts a one-line test broadcast.
4. Optionally installs + enables a systemd timer that fires nightly at **21:00 local**.

Full walkthrough in [docs/INSTALL.md](docs/INSTALL.md).

---

## Detailed config

Every knob is documented in [docs/CONFIGURATION.md](docs/CONFIGURATION.md). The shape:

```yaml
calendar:
  url: "${CALENDAR_URL}"
  timeout_seconds: 15
  max_attempts: 3

meshmonitor:
  url: http://localhost:8080
  api_token: "${MESHMONITOR_API_TOKEN}"
  channel_index: 0          # 0 = primary

message:
  greeting: "Goodnight mesh! Tomorrow:"
  no_events_suffix: "Nothing scheduled"
  reply_hint: "DM 'forekast tomorrow' for full list"
  max_events: 2
  max_chars: 200

timezone: "America/Phoenix"
```

Environment variables override YAML — rotate tokens without touching files.

---

## What it broadcasts

Single line, ≤200 bytes (Meshtastic-friendly), UTF-8-byte-safe truncation that won't emit a half-emoji.

```
Goodnight mesh! Tomorrow: Solar eclipse viewing party. Backyard cookout 6pm. DM 'forekast tomorrow' for full list
Goodnight mesh! Tomorrow: Nothing scheduled. DM 'forekast tomorrow' for full list
Goodnight mesh! Tomorrow: AZ Mesh meetup 6pm @ Snooze. Astro night @ South Mtn (+3 more). DM 'forekast tomorrow' for full list
```

If the calendar is unreachable at broadcast time, the mesh still gets a goodnight ping (silence is worse than a degraded message) — the message falls back to the no-events branch and the failure is logged.

---

## What time it fires

Default schedule via systemd timer: **21:00 local** (9pm), every night.

```ini
OnCalendar=*-*-* 21:00:00
Persistent=true
RandomizedDelaySec=60s
```

`Persistent=true` means if the host was off at 9pm, the broadcast fires as soon as the host is back. Adjust the time by editing `/etc/systemd/system/forekast-mesh-goodnight.timer` after install.

If you prefer cron, see [docs/INSTALL.md](docs/INSTALL.md#cron).

---

## CLI

```
forekast-mesh post-goodnight            # one-shot — fetch + post tomorrow's events
forekast-mesh post-goodnight --dry-run  # format + print, do not send
forekast-mesh doctor                    # verify calendar + MeshMonitor + test ping
forekast-mesh test-format               # fetch + format, do not send
forekast-mesh install-systemd           # copy + enable the nightly timer
```

---

## Backends

**MeshMonitor abstracts storage**, so this package speaks a single HTTP interface regardless of how MeshMonitor stores data:

- **Postgres-backed MeshMonitor** — typical for fixed home / production installs with multi-week history retention.
- **SQLite-backed MeshMonitor** — typical for mobile / RV / single-Pi installs.

We talk to `POST /api/v1/messages` + `GET /api/v1/nodes` (used by `doctor`) — both backends serve identical responses. No backend-specific configuration needed in this package.

---

## Architecture

```
+------------+   GET     +----------------+   POST /api/v1/messages   +-------------+
|  ICS feed  | --------> | forekast-mesh  | ------------------------> | MeshMonitor | --> Meshtastic mesh
|  (Forekast,|   fetch   |  (this pkg)    |                           |  (Yeraze)   |
|   Google,  |           |                |                           |             |
|   CalDAV)  |           |                |                           |             |
+------------+           +----------------+                           +-------------+
                                |
                                v
                        once-per-day cron/systemd
```

Single-shot design — no daemons, no in-process schedulers. Cron or `systemd.timer` is the source of truth for "when".

---

## Companion DM auto-responder

The default `reply_hint` is `DM 'forekast tomorrow' for full list`. Wire it up in MeshMonitor with a tiny script (the ICS parsing logic ships in `forecast_client.py` — easy to lift into a 60-line standalone). See [docs/CONFIGURATION.md](docs/CONFIGURATION.md#companion-dm-auto-responder).

If you don't want a DM auto-responder, just clear `reply_hint` and the broadcast won't advertise one.

---

## Roadmap

Open contribution invite. Known wants:

- [ ] Built-in Dockerfile + GitHub-published image.
- [ ] Multiple calendar sources merged into one message.
- [ ] Per-channel routing rules (events on Community channel, summary on Primary).
- [ ] Pluggable formatters (markdown / numbered list / emoji-heavy).
- [ ] Optional dependency on [tempest-meshtastic-weather](https://github.com/rancur/tempest-meshtastic-weather) for a "goodnight + tomorrow's forecast + tomorrow's events" combined message.

PRs welcome. The test suite mocks all network calls, so any contribution can be verified locally with `pytest -q`.

---

## Sibling projects

- [tempest-meshtastic-weather](https://github.com/rancur/tempest-meshtastic-weather) — the WeatherFlow Tempest broadcaster the MeshMonitor client pattern came from. If you're running both, they share zero state — drop them on the same host with separate systemd timers.

---

## Credits

- [Forekast](https://forekast.com/) for the public-events calendar feed that inspired this.
- [Yeraze/meshmonitor](https://github.com/Yeraze/meshmonitor) for the MeshMonitor HTTP API this depends on.
- [Meshtastic](https://meshtastic.org/) for the off-grid mesh that makes this useful.
- [icalendar](https://github.com/collective/icalendar) for the ICS parser.

---

## License

[MIT](LICENSE)
