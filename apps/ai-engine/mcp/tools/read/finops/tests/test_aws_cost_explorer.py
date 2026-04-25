"""Tests for ``query_aws_costs`` backed by moto's Cost Explorer mock.

Moto's Cost Explorer backend is minimal but sufficient for round-
tripping ``get_cost_and_usage`` with the request shape we send.
Tests never hit the network.
"""

from __future__ import annotations

import importlib
import json
import os

import pytest

boto3 = pytest.importorskip("boto3")
moto = pytest.importorskip("moto")

from mcp.tools.read.finops import aws_cost_explorer  # noqa: E402
from mcp.tools.read.finops.config import FinOpsConfig, set_config  # noqa: E402


@pytest.fixture
def aws_env(monkeypatch):
    """Stub AWS credentials so boto3 picks them up cleanly under moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    # Ensure any host profile env doesn't shadow us.
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    set_config(FinOpsConfig(aws_region="us-east-1", aws_profile=None))


def _mock_ce():
    """Pick the mock_aws / mock_ce decorator that's available."""
    if hasattr(moto, "mock_aws"):
        return moto.mock_aws()
    return moto.mock_ce()  # pragma: no cover


def test_query_aws_costs_returns_json_dict(aws_env):
    with _mock_ce():
        result = aws_cost_explorer.query_aws_costs(
            start_date="2026-04-01",
            end_date="2026-04-25",
            granularity="DAILY",
        )
    # Must be fully JSON-serialisable.
    json.dumps(result)
    assert result["status"] == "success"
    assert result["tool"] == "query_aws_costs"
    assert result["backend"] == "aws_cost_explorer"
    assert result["start_date"] == "2026-04-01"
    assert result["end_date"] == "2026-04-25"
    assert result["granularity"] == "DAILY"
    # moto returns an empty or synthetic result — both are fine.
    assert "results" in result
    assert isinstance(result["results"], list)
    assert isinstance(result["total_cost"], (int, float))


def test_query_aws_costs_with_service_filter(aws_env):
    with _mock_ce():
        result = aws_cost_explorer.query_aws_costs(
            start_date="2026-04-01",
            end_date="2026-04-25",
            service="Amazon Elastic Compute Cloud - Compute",
        )
    assert result["status"] == "success"
    assert result["service_filter"] == "Amazon Elastic Compute Cloud - Compute"


def test_query_aws_costs_with_group_by(aws_env):
    with _mock_ce():
        result = aws_cost_explorer.query_aws_costs(
            start_date="2026-04-01",
            end_date="2026-04-25",
            group_by=["SERVICE"],
        )
    assert result["status"] == "success"
    assert result["group_by"] == ["SERVICE"]


def test_missing_credentials_returns_unavailable(monkeypatch):
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("AWS_SESSION_TOKEN", raising=False)
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    # Point config at a region with no real creds and NO moto.
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
    monkeypatch.setenv("AWS_STS_REGIONAL_ENDPOINTS", "regional")
    # A bogus region + explicit profile that does not exist forces a
    # credentials failure without hitting the network.
    monkeypatch.setenv("AEGIS_FINOPS_AWS_PROFILE", "does-not-exist-profile")
    from mcp.tools.read.finops import config as cfg_mod

    cfg_mod.reset_config()
    result = aws_cost_explorer.query_aws_costs(
        start_date="2026-04-01",
        end_date="2026-04-25",
    )
    assert result["status"] == "unavailable"
    assert result["tool"] == "query_aws_costs"
    assert result["backend"] == "aws_cost_explorer"


def test_boto3_missing_returns_unavailable(monkeypatch):
    """If boto3 cannot be imported, the tool still returns a clean dict."""
    monkeypatch.setattr(aws_cost_explorer, "_HAS_BOTO3", False)
    result = aws_cost_explorer.query_aws_costs(
        start_date="2026-04-01",
        end_date="2026-04-25",
    )
    assert result["status"] == "unavailable"
    assert "boto3" in result["reason"]
    assert result.get("install_hint") == "pip install aegis-ai-engine[finops]"


def test_module_reimport_is_idempotent():
    """Re-importing the module must not double-register the tool."""
    import mcp.manifest as mm

    before = [
        t for t in mm.manifest.get_all_loaded() if t.name == "query_aws_costs"
    ]
    importlib.reload(aws_cost_explorer)
    after = [
        t for t in mm.manifest.get_all_loaded() if t.name == "query_aws_costs"
    ]
    assert len(before) == 1
    assert len(after) == 1


def _unused_placeholder():
    # Guard against accidental `os` import-only lint noise.
    _ = os.environ.get("PYTHONPATH")
