# Troubleshooting

Run `forekast-mesh doctor` first — it isolates the failure to calendar fetch, MeshMonitor reach, or MeshMonitor write.

## Calendar fetch fails

- **`calendar.url is empty`** — set `CALENDAR_URL` in `.env` or `calendar.url` in `config.yaml`.
- **`fetch failed after N attempts`** — the ICS URL is unreachable. Test with `curl -v "$CALENDAR_URL"`. Common causes: typo, firewall, expired Google Calendar secret link.
- **Empty result on a day you expect events** — verify `GOODNIGHT_TZ` is correct. Forekast events are local-day; a UTC host fires at 21:00 UTC which is "tomorrow already" in some timezones.

## MeshMonitor failures

- **`MESHMONITOR_API_TOKEN is required`** — set the token in `.env`. In MeshMonitor, generate it under Settings → API.
- **`Connection refused`** — verify `MESHMONITOR_URL` includes the right port (`http://192.168.1.x:8080` by default). From the install host: `curl "$MESHMONITOR_URL/api/v1/nodes" -H "Authorization: Bearer $MESHMONITOR_API_TOKEN"`.
- **`success: false` in MeshMonitor response** — usually means MeshMonitor's connection to the Meshtastic node is down. Check MeshMonitor's UI; the node should show as "connected". The 3-attempt + 30s backoff is tuned for short MeshMonitor↔node hiccups, but won't paper over a dead radio.

## systemd timer not firing

```bash
systemctl list-timers forekast-mesh-goodnight.timer
systemctl status forekast-mesh-goodnight.service
journalctl -u forekast-mesh-goodnight.service --since today
```

- **No `LAST` column value after the scheduled time** — timer is enabled but not started. `sudo systemctl start forekast-mesh-goodnight.timer`.
- **Service ran but no broadcast** — check the journal. The most common cause is `.env` not being loaded; `EnvironmentFile=` is `-` prefixed (optional), so a missing `.env` is silent. Confirm with `systemctl cat forekast-mesh-goodnight.service`.
- **Wrong time** — `OnCalendar=*-*-* 21:00:00` uses the system timezone. Either change the unit `OnCalendar=` or set `TZ` system-wide.

## Tests fail on a fresh clone

```bash
./scripts/test-install.sh
```

This bootstraps a throwaway venv, installs the package, runs the suite. If it fails, paste the output into an issue.

## Message is truncated weirdly

- The formatter targets `message.max_chars` BYTES (UTF-8 length), not characters. Emojis cost 4 bytes each.
- If you see `(+N more)` disappearing on long event names, that's by design — when both the events and the suffix can't both fit, the suffix is dropped first to keep maximum event content.
- To always keep `(+N more)`, lower `message.max_events` or `message.max_event_chars`.

## Calendar has events but message says "Nothing scheduled"

Either:

1. The events are for a different day than you think (check `GOODNIGHT_TZ`).
2. The events are all-day events on a different date and dtstart vs. dtend confused the parser. Open an issue with a minimal `.ics` reproducer.
3. The ICS feed serves an HTML error page instead of an `.ics`. `curl -v "$CALENDAR_URL"` to confirm `Content-Type: text/calendar`.
