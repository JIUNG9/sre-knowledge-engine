"""Tests for ``query_opencost_allocation`` with respx-mocked HTTP."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from mcp.tools.read.finops import opencost
from mcp.tools.read.finops.config import FinOpsConfig, set_config


OPENCOST_URL = "http://opencost.opencost.svc.cluster.local:9003"


@pytest.fixture
def configured():
    set_config(FinOpsConfig(opencost_url=OPENCOST_URL))


@respx.mock
def test_query_opencost_happy_path(configured):
    body = {
        "code": 200,
        "data": [
            {
                "acme-web": {
                    "name": "acme-web",
                    "cpuCost": 12.5,
                    "gpuCost": 0,
                    "ramCost": 4.0,
                    "pvCost": 1.5,
                    "networkCost": 0.25,
                    "sharedCost": 0,
                },
                "customer-xyz-api": {
                    "name": "customer-xyz-api",
                    "cpuCost": 30.0,
                    "ramCost": 10.0,
                },
            }
        ],
    }
    respx.get(f"{OPENCOST_URL}/allocation/compute").mock(
        return_value=httpx.Response(200, json=body)
    )

    result = opencost.query_opencost_allocation(window="7d", aggregate="namespace")
    json.dumps(result)

    assert result["status"] == "success"
    assert result["tool"] == "query_opencost_allocation"
    assert result["backend"] == "opencost"
    assert result["window"] == "7d"
    assert result["aggregate"] == "namespace"
    assert result["raw_record_count"] == 2
    # The larger namespace should be ranked first.
    assert result["allocations"][0]["name"] == "customer-xyz-api"
    assert result["allocations"][0]["total_cost"] == 40.0
    assert result["total_cost"] == 18.25 + 40.0


def test_unconfigured_backend_returns_unavailable():
    set_config(FinOpsConfig(opencost_url=None))
    result = opencost.query_opencost_allocation()
    assert result["status"] == "unavailable"
    assert "OPENCOST" in result["reason"]


@respx.mock
def test_http_error_returns_unavailable(configured):
    respx.get(f"{OPENCOST_URL}/allocation/compute").mock(
        return_value=httpx.Response(500, text="boom")
    )
    result = opencost.query_opencost_allocation()
    assert result["status"] == "unavailable"
    assert "HTTP 500" in result["reason"]


@respx.mock
def test_network_error_returns_unavailable(configured):
    respx.get(f"{OPENCOST_URL}/allocation/compute").mock(
        side_effect=httpx.ConnectError("no route")
    )
    result = opencost.query_opencost_allocation()
    assert result["status"] == "unavailable"
    assert "request failed" in result["reason"]


@respx.mock
def test_non_json_body_returns_unavailable(configured):
    respx.get(f"{OPENCOST_URL}/allocation/compute").mock(
        return_value=httpx.Response(
            200,
            text="<html>not json</html>",
            headers={"content-type": "text/html"},
        )
    )
    result = opencost.query_opencost_allocation()
    assert result["status"] == "unavailable"
    assert "non-JSON" in result["reason"]
