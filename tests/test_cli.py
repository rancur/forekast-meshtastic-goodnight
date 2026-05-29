"""Tests for the ``forekast-mesh`` CLI."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from forekast_mesh.__main__ import cli
from forekast_mesh.goodnight_poster import PostResult


@pytest.fixture
def isolated_runner(tmp_path, monkeypatch):
    """A CliRunner pinned to a clean tmp_path cwd so config.yaml doesn't leak in."""
    monkeypatch.chdir(tmp_path)
    return CliRunner()


def test_cli_version(isolated_runner: CliRunner) -> None:
    result = isolated_runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "forekast-mesh" in result.output


def test_cli_help(isolated_runner: CliRunner) -> None:
    result = isolated_runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "post-goodnight" in result.output
    assert "doctor" in result.output
    assert "test-format" in result.output
    assert "install-systemd" in result.output


def test_cli_post_goodnight_dry_run(isolated_runner: CliRunner) -> None:
    fake_result = PostResult(success=True, message="fake goodnight", sent=False)
    with patch(
        "forekast_mesh.__main__.post_goodnight", return_value=fake_result
    ) as poster:
        result = isolated_runner.invoke(cli, ["post-goodnight", "--dry-run"])
    assert result.exit_code == 0
    assert "fake goodnight" in result.output
    assert poster.call_args.kwargs.get("dry_run") is True


def test_cli_post_goodnight_failure_exits_nonzero(isolated_runner: CliRunner) -> None:
    fake_result = PostResult(
        success=False, message="degraded msg", reason="meshmonitor down", sent=False
    )
    with patch("forekast_mesh.__main__.post_goodnight", return_value=fake_result):
        result = isolated_runner.invoke(cli, ["post-goodnight"])
    assert result.exit_code == 1
    assert "meshmonitor down" in result.output


def test_cli_test_format_uses_dry_run(isolated_runner: CliRunner) -> None:
    fake_result = PostResult(success=True, message="formatted", sent=False)
    with patch(
        "forekast_mesh.__main__.post_goodnight", return_value=fake_result
    ) as poster:
        result = isolated_runner.invoke(cli, ["test-format"])
    assert result.exit_code == 0
    assert "formatted" in result.output
    assert poster.call_args.kwargs.get("dry_run") is True
