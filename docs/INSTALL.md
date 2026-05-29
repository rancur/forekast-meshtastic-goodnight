# Install

forekast-meshtastic-goodnight is a single-binary Python package. Two install paths: scripted (recommended) and manual.

## Prerequisites

- **Python 3.10+** on the host that will run the broadcast.
- **MeshMonitor** (https://github.com/Yeraze/meshmonitor) reachable from this host, with `MM_API_TOKEN` set.
- A **public ICS calendar URL** — Forekast.com profiles expose one at `https://forekast.com/<handle>/calendar.ics`. Any ICS feed works.

## Scripted install

```bash
git clone https://github.com/rancur/forekast-meshtastic-goodnight.git
cd forekast-meshtastic-goodnight
./scripts/install.sh
```

The installer:

1. Builds a `.venv`, installs the package, registers the `forekast-mesh` CLI.
2. Prompts for the bare minimum: ICS URL, MeshMonitor URL + token, timezone.
3. Writes `.env` (mode 0600) and `config.yaml`.
4. Optionally runs `forekast-mesh doctor` to verify both sides reachable + posts a one-line test broadcast.
5. Optionally installs + enables the systemd timer (`forekast-mesh-goodnight.timer`).

## Manual install

```bash
git clone https://github.com/rancur/forekast-meshtastic-goodnight.git
cd forekast-meshtastic-goodnight
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp config.example.yaml config.yaml
cp .env.example .env       # then edit
chmod 600 .env

# Smoke test
forekast-mesh --version
forekast-mesh post-goodnight --dry-run

# Verify both ends
forekast-mesh doctor

# Once happy, send for real
forekast-mesh post-goodnight
```

## Schedule

Two equivalent options.

### systemd timer (recommended)

```bash
sudo forekast-mesh install-systemd --working-dir "$(pwd)"
```

Defaults to **21:00 local time**, daily, with `Persistent=true` (catches up after a reboot) and a 60-second random delay.

To change the time, edit `/etc/systemd/system/forekast-mesh-goodnight.timer` after install and `systemctl daemon-reload`.

### cron

```cron
0 21 * * * cd /opt/forekast-meshtastic-goodnight && .venv/bin/forekast-mesh post-goodnight >> /var/log/forekast-mesh.log 2>&1
```

## Docker

This repo doesn't ship a Dockerfile yet (PRs welcome), but the package is plain Python — drop it into any `python:3.12-slim` base image, expose the env vars listed in `.env.example`, and run `forekast-mesh post-goodnight` from a cron container (e.g. `mcuadros/ofelia`).

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
