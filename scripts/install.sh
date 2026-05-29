#!/usr/bin/env bash
# forekast-meshtastic-goodnight installer.
# Idempotent. Safe to re-run. Asks the bare minimum and writes config.yaml + .env.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

green() { printf "\033[32m%s\033[0m\n" "$*"; }
red()   { printf "\033[31m%s\033[0m\n" "$*"; }
bold()  { printf "\033[1m%s\033[0m\n" "$*"; }
ask() {
  # ask <prompt> <var-name> [default]
  local prompt="$1" var="$2" default="${3:-}"
  local val
  if [[ -n "$default" ]]; then
    read -rp "$prompt [$default]: " val
    val="${val:-$default}"
  else
    read -rp "$prompt: " val
  fi
  printf -v "$var" '%s' "$val"
}

bold "forekast-meshtastic-goodnight — interactive installer"
echo "Repo root: $REPO_ROOT"
echo

# --- 1. Python venv -----------------------------------------------------------
PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  red "python3 not found on PATH; install Python 3.10+ first."
  exit 2
fi

if [[ ! -d .venv ]]; then
  echo "Creating .venv via $PYTHON -m venv..."
  "$PYTHON" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet --upgrade pip
echo "Installing package + deps..."
pip install --quiet -e ".[dev]"

green "  -> .venv ready, forekast-mesh CLI available"

# --- 2. config / env ---------------------------------------------------------
if [[ -f .env ]]; then
  echo
  bold "Detected existing .env — keeping it. Edit by hand or delete to re-run prompts."
else
  echo
  bold "Let's collect the bare minimum config. (You can edit .env later for everything else.)"

  ask "Public ICS calendar URL (e.g. https://forekast.com/<handle>/calendar.ics)" CALENDAR_URL
  ask "MeshMonitor URL" MESHMONITOR_URL "http://localhost:8080"
  ask "MeshMonitor API token (Yeraze/meshmonitor MM_API_TOKEN)" MESHMONITOR_API_TOKEN
  ask "Default channel index (0 = primary)" MESHMONITOR_CHANNEL_INDEX 0
  ask "Timezone (IANA, e.g. America/Phoenix, Europe/London)" GOODNIGHT_TZ "America/Phoenix"
  ask "Greeting line" MESSAGE_GREETING "Goodnight mesh! Tomorrow:"
  ask "Reply hint (optional, leave blank for none)" MESSAGE_REPLY_HINT "DM 'forekast tomorrow' for full list"
  ask "Max events to include" MESSAGE_MAX_EVENTS 2

  cat > .env <<EOF
CALENDAR_URL=${CALENDAR_URL}
MESHMONITOR_URL=${MESHMONITOR_URL}
MESHMONITOR_API_TOKEN=${MESHMONITOR_API_TOKEN}
MESHMONITOR_CHANNEL_INDEX=${MESHMONITOR_CHANNEL_INDEX}
GOODNIGHT_TZ=${GOODNIGHT_TZ}
MESSAGE_GREETING=${MESSAGE_GREETING}
MESSAGE_REPLY_HINT=${MESSAGE_REPLY_HINT}
MESSAGE_MAX_EVENTS=${MESSAGE_MAX_EVENTS}
EOF
  chmod 600 .env
  green "  -> wrote .env (permissions 600). Edit any time."
fi

if [[ ! -f config.yaml ]]; then
  cp config.example.yaml config.yaml
  green "  -> wrote config.yaml from example. Override anything via .env."
fi

# --- 3. doctor check ----------------------------------------------------------
echo
bold "Running 'forekast-mesh doctor' to verify calendar + MeshMonitor connectivity..."
echo "(Will post a one-line test broadcast to your mesh.)"
read -rp "Run doctor now? [Y/n]: " run_doctor
run_doctor="${run_doctor:-Y}"
if [[ "$run_doctor" =~ ^[Yy]$ ]]; then
  set -a; source .env; set +a
  forekast-mesh doctor || { red "doctor failed — fix the errors above before continuing."; exit 1; }
fi

# --- 4. optional systemd ------------------------------------------------------
echo
bold "Install systemd timer so this fires nightly at 21:00 local?"
echo "(Requires sudo. Skip if you'd rather wire your own cron / Docker.)"
read -rp "Install systemd timer? [y/N]: " want_systemd
want_systemd="${want_systemd:-N}"
if [[ "$want_systemd" =~ ^[Yy]$ ]]; then
  if [[ "$EUID" -ne 0 ]]; then
    echo "Re-running install as sudo for systemd..."
    sudo -E env "PATH=$PATH" forekast-mesh install-systemd --working-dir "$REPO_ROOT"
  else
    forekast-mesh install-systemd --working-dir "$REPO_ROOT"
  fi
fi

echo
green "Done. Try: forekast-mesh post-goodnight --dry-run"
