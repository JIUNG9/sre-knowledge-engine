"""Tests for ``query_kubecost_allocation`` with respx-mocked HTTP."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from mcp.tools.read.finops import kubecost
from mcp.tools.read.finops.config import FinOpsConfig, set_config


KUBECOST_URL = "http://kubecost-cost-analyzer.kubecost.svc.cluster.local:9090"


@pytest.fixture
def configured():
    set_config(FinOpsConfig(kubecost_url=KUBECOST_URL))


@respx.mock
def test_query_kubecost_happy_path(configured):
    body = {
        "code": 200,
        "data": [
            {
                "acme-corp-platform": {
                    "name": "acme-corp-platform",
                    "cpuCost": 50.0,
                    "ramCost": 20.0,
                    "pvCost": 5.0,
                },
                "customer-xyz-batch": {
                    "name": "customer-xyz-batch",
                    "cpuCost": 15.0,
                    "gpuCost": 60.0,
                    "ramCost": 5.0,
                },
            }
        ],
    }
    respx.get(f"{KUBECOST_URL}/model/allocation").mock(
        return_value=httpx.Response(200, json=body)
    )

    result = kubecost.query_kubecost_allocation(window="7d", aggregate="namespace")
    json.dumps(result)

    assert result["status"] == "success"
    assert result["backend"] == "kubecost"
    assert result["aggregate"] == "namespace"
    # customer-xyz-batch has a GPU cost driving a higher total.
    assert result["allocations"][0]["name"] == "customer-xyz-batch"
    assert result["allocations"][0]["total_cost"] == 80.0
    assert result["total_cost"] == 75.0 + 80.0


def test_unconfigured_backend_returns_unavailable():
    set_config(FinOpsConfig(kubecost_url=None))
    result = kubecost.query_kubecost_allocation()
    assert result["status"] == "unavailable"
    assert "KUBECOST" in result["reason"]


@respx.mock
def test_http_error_returns_unavailable(configured):
    respx.get(f"{KUBECOST_URL}/model/allocation").mock(
        return_value=httpx.Response(503, text="backend busy")
    )
    result = kubecost.query_kubecost_allocation()
    assert result["status"] == "unavailable"
    assert "HTTP 503" in result["reason"]


@respx.mock
def test_network_error_returns_unavailable(configured):
    respx.get(f"{KUBECOST_URL}/model/allocation").mock(
        side_effect=httpx.ConnectTimeout("timeout")
    )
    result = kubecost.query_kubecost_allocation()
    assert result["status"] == "unavailable"
    assert "request failed" in result["reason"]


@respx.mock
def test_alternate_aggregate_label(configured):
    body = {"code": 200, "data": [{"team-a": {"cpuCost": 1.0}}]}
    respx.get(f"{KUBECOST_URL}/model/allocation").mock(
        return_value=httpx.Response(200, json=body)
    )
    result = kubecost.query_kubecost_allocation(aggregate="label:team")
    assert result["aggregate"] == "label:team"
    assert result["allocations"][0]["name"] == "team-a"
