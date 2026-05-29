"""Tests for ``forekast_mesh.meshmonitor_client``."""

from __future__ import annotations

import pytest
import requests_mock

from forekast_mesh.config import AppConfig
from forekast_mesh.meshmonitor_client import MeshMonitorClient, MeshMonitorError


def test_post_message_requires_token(minimal_config: AppConfig) -> None:
    mm = MeshMonitorClient(minimal_config)
    with pytest.raises(MeshMonitorError):
        mm.post_message("hi")


def test_post_message_success(stub_config: AppConfig) -> None:
    mm = MeshMonitorClient(stub_config)
    with requests_mock.Mocker() as m:
        m.post(
            f"{stub_config.meshmonitor.url}/api/v1/messages",
            json={"success": True},
        )
        assert mm.post_message("hello mesh") is True


def test_post_message_retries_then_succeeds(stub_config: AppConfig) -> None:
    mm = MeshMonitorClient(stub_config)
    with requests_mock.Mocker() as m:
        m.post(
            f"{stub_config.meshmonitor.url}/api/v1/messages",
            [
                {"status_code": 503, "text": "down"},
                {"status_code": 200, "json": {"success": True}},
            ],
        )
        assert mm.post_message("hello mesh") is True


def test_post_message_all_attempts_fail_returns_false(stub_config: AppConfig) -> None:
    mm = MeshMonitorClient(stub_config)
    with requests_mock.Mocker() as m:
        m.post(
            f"{stub_config.meshmonitor.url}/api/v1/messages",
            status_code=503,
            text="down",
        )
        assert mm.post_message("hello mesh") is False


def test_post_message_success_false_body_returns_false(stub_config: AppConfig) -> None:
    mm = MeshMonitorClient(stub_config)
    with requests_mock.Mocker() as m:
        m.post(
            f"{stub_config.meshmonitor.url}/api/v1/messages",
            json={"success": False, "error": "channel full"},
        )
        assert mm.post_message("hello mesh") is False


def test_post_message_sends_bearer_header(stub_config: AppConfig) -> None:
    mm = MeshMonitorClient(stub_config)
    with requests_mock.Mocker() as m:
        m.post(
            f"{stub_config.meshmonitor.url}/api/v1/messages",
            json={"success": True},
        )
        mm.post_message("hi")
        assert m.last_request.headers["Authorization"] == f"Bearer {stub_config.meshmonitor.api_token}"


def test_post_message_sends_payload(stub_config: AppConfig) -> None:
    mm = MeshMonitorClient(stub_config)
    with requests_mock.Mocker() as m:
        m.post(
            f"{stub_config.meshmonitor.url}/api/v1/messages",
            json={"success": True},
        )
        mm.post_message("payload-test", channel_index=4)
        body = m.last_request.json()
    assert body["text"] == "payload-test"
    assert body["channel"] == 4


def test_list_nodes_parses_response(stub_config: AppConfig) -> None:
    mm = MeshMonitorClient(stub_config)
    payload = {
        "data": [
            {"nodeId": "!12ab34cd", "role": 0, "hopsAway": None, "lastHeard": 1717000000},
            {"nodeId": "!aabbccdd", "role": 1, "hopsAway": 2, "lastHeard": 1717001000},
        ]
    }
    with requests_mock.Mocker() as m:
        m.get(f"{stub_config.meshmonitor.url}/api/v1/nodes", json=payload)
        nodes = mm.list_nodes()
    assert len(nodes) == 2
    assert nodes[0].node_id == "!12ab34cd"
    assert nodes[0].role == 0
    assert nodes[1].hops_away == 2


def test_list_nodes_requires_token(minimal_config: AppConfig) -> None:
    mm = MeshMonitorClient(minimal_config)
    with pytest.raises(MeshMonitorError):
        mm.list_nodes()
