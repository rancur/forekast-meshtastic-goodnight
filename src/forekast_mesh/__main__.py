"""``forekast-mesh`` CLI."""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from pathlib import Path

import click

from . import __version__
from .config import load_config
from .forecast_client import ForecastClient, ForecastFetchError
from .goodnight_poster import post_goodnight
from .meshmonitor_client import MeshMonitorClient


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


@click.group()
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Path to config.yaml. Defaults to ./config.yaml if present, else env-only.",
)
@click.version_option(version=__version__, prog_name="forekast-mesh")
@click.pass_context
def cli(ctx: click.Context, config_path: Path | None) -> None:
    """Nightly Meshtastic goodnight broadcast — tomorrow's events from any ICS feed."""
    cfg = load_config(config_path)
    _setup_logging(cfg.logging.level)
    ctx.ensure_object(dict)
    ctx.obj["config"] = cfg


@cli.command("post-goodnight")
@click.option("--dry-run", is_flag=True, help="Format + print only; do not send.")
@click.pass_context
def post_goodnight_cmd(ctx: click.Context, dry_run: bool) -> None:
    """One-shot: fetch tomorrow's events and post the goodnight broadcast."""
    cfg = ctx.obj["config"]
    result = post_goodnight(cfg, dry_run=dry_run)
    click.echo(result.message)
    if not result.success and not dry_run:
        click.echo(f"failed: {result.reason}", err=True)
        sys.exit(1)


@cli.command("test-format")
@click.pass_context
def test_format_cmd(ctx: click.Context) -> None:
    """Fetch + format the goodnight message but DO NOT send."""
    cfg = ctx.obj["config"]
    result = post_goodnight(cfg, dry_run=True)
    click.echo(result.message)
    if not result.success:
        click.echo(f"warning: {result.reason}", err=True)
        sys.exit(1)


@cli.command("doctor")
@click.pass_context
def doctor_cmd(ctx: click.Context) -> None:
    """Sanity-check config: calendar reachable, MeshMonitor reachable, send a test ping."""
    cfg = ctx.obj["config"]
    problems: list[str] = []

    click.echo(click.style("=== forekast-mesh doctor ===", bold=True))
    click.echo(f"Calendar URL:   {cfg.calendar.url or '(unset)'}")
    click.echo(f"MeshMonitor:    {cfg.meshmonitor.url}")
    click.echo(f"Channel index:  {cfg.meshmonitor.channel_index}")
    click.echo(f"Timezone:       {cfg.timezone}")
    click.echo()

    # 1. Calendar
    click.echo("[1/3] Probing ICS calendar...")
    fc = ForecastClient(cfg)
    try:
        ics = fc.fetch_ics()
        tomorrow = fc.get_tomorrow()
        events = fc.events_for_date(ics, tomorrow)
        click.echo(
            click.style(
                f"  OK — {len(ics)} bytes fetched; {len(events)} event(s) for {tomorrow}",
                fg="green",
            )
        )
        for e in events[:10]:
            click.echo(f"    - {e}")
    except ForecastFetchError as e:
        click.echo(click.style(f"  FAIL — {e}", fg="red"))
        problems.append(f"calendar: {e}")
    except Exception as e:  # pragma: no cover — defensive
        click.echo(click.style(f"  FAIL — unexpected error: {e}", fg="red"))
        problems.append(f"calendar: {e}")

    # 2. MeshMonitor nodes
    click.echo("[2/3] Probing MeshMonitor /api/v1/nodes...")
    mm = MeshMonitorClient(cfg)
    try:
        nodes = mm.list_nodes()
        click.echo(click.style(f"  OK — {len(nodes)} node(s) visible", fg="green"))
        for n in nodes[:10]:
            click.echo(f"    - {n.node_id}  role={n.role}  hops={n.hops_away}")
    except Exception as e:
        click.echo(click.style(f"  FAIL — {e}", fg="red"))
        problems.append(f"meshmonitor nodes: {e}")

    # 3. Test post
    click.echo("[3/3] Posting a one-line test broadcast...")
    test_msg = "TEST: forekast-mesh doctor — please ignore"
    try:
        ok = mm.post_message(test_msg, label="doctor-test")
        if ok:
            click.echo(click.style("  OK — test broadcast accepted", fg="green"))
        else:
            click.echo(click.style("  FAIL — MeshMonitor refused the post", fg="red"))
            problems.append("meshmonitor post returned failure")
    except Exception as e:
        click.echo(click.style(f"  FAIL — {e}", fg="red"))
        problems.append(f"meshmonitor post: {e}")

    click.echo()
    if problems:
        click.echo(click.style(f"{len(problems)} problem(s) found:", fg="red", bold=True))
        for p in problems:
            click.echo(f"  - {p}")
        sys.exit(1)
    click.echo(click.style("all checks passed", fg="green", bold=True))


@cli.command("install-systemd")
@click.option(
    "--prefix",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("/etc/systemd/system"),
    help="Where to copy the unit files.",
)
@click.option(
    "--user",
    default="forekastmesh",
    help="User the units will run as.",
)
@click.option(
    "--working-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path.cwd(),
    help="WorkingDirectory for the units (where config.yaml lives).",
)
@click.option("--no-enable", is_flag=True, help="Copy but don't enable/start.")
def install_systemd_cmd(prefix: Path, user: str, working_dir: Path, no_enable: bool) -> None:
    """Render + install systemd units. Requires root (or sudo)."""
    src_dir = Path(__file__).resolve().parent.parent.parent / "systemd"
    if not src_dir.is_dir():
        click.echo(f"systemd templates dir not found at {src_dir}", err=True)
        sys.exit(2)

    binary = shutil.which("forekast-mesh") or sys.executable + " -m forekast_mesh"

    units = [
        "forekast-mesh-goodnight.service",
        "forekast-mesh-goodnight.timer",
    ]
    for unit in units:
        src = src_dir / unit
        if not src.exists():
            click.echo(f"missing template {src}", err=True)
            sys.exit(2)
        rendered = src.read_text().format(
            user=user,
            working_dir=str(working_dir),
            binary=binary,
        )
        dst = prefix / unit
        dst.write_text(rendered)
        click.echo(f"wrote {dst}")

    if no_enable:
        return
    for action, unit in [
        ("daemon-reload", None),
        ("enable", "forekast-mesh-goodnight.timer"),
        ("start", "forekast-mesh-goodnight.timer"),
    ]:
        cmd = ["systemctl", action]
        if unit:
            cmd.append(unit)
        click.echo("$ " + " ".join(cmd))
        subprocess.run(cmd, check=False)


def main() -> None:  # pragma: no cover
    cli(obj={})


if __name__ == "__main__":  # pragma: no cover
    main()


__all__ = ["cli", "main"]
