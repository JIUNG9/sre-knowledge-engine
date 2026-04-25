"""Tests for the ``top_spenders`` composite tool.

The composite tool is tested with its sub-tools monkeypatched — we
don't care about the individual backends here (those are covered by
``test_aws_cost_explorer``, ``test_opencost``, ``test_kubecost``).
"""

from __future__ import annotations

import json

import importlib

ts = importlib.import_module("mcp.tools.read.finops.top_spenders")


def _aws_result(**_):
    return {
        "status": "success",
        "tool": "query_aws_costs",
        "total_cost": 123.45,
        "currency": "USD",
        "results": [
            {"start": "2026-04-18", "end": "2026-04-19", "keys": ["AmazonEC2"], "amount": 80.0, "currency": "USD"},
            {"start": "2026-04-18", "end": "2026-04-19", "keys": ["AmazonRDS"], "amount": 30.0, "currency": "USD"},
            {"start": "2026-04-18", "end": "2026-04-19", "keys": ["AmazonS3"], "amount": 13.45, "currency": "USD"},
        ],
    }


def _opencost_result(**_):
    return {
        "status": "success",
        "tool": "query_opencost_allocation",
        "total_cost": 90.0,
        "currency": "USD",
        "allocations": [
            {"name": "acme-web", "total_cost": 60.0},
            {"name": "customer-xyz", "total_cost": 30.0},
        ],
    }


def _kubecost_result(**_):
    return {
        "status": "success",
        "tool": "query_kubecost_allocation",
        "total_cost": 50.0,
        "currency": "USD",
        "allocations": [{"name": "acme-web", "total_cost": 50.0}],
    }


def _unavailable(**_):
    return {
        "status": "unavailable",
        "reason": "not configured",
    }


def test_top_spenders_fanout_all(monkeypatch):
    monkeypatch.setattr(ts, "query_aws_costs", _aws_result)
    monkeypatch.setattr(ts, "query_opencost_allocation", _opencost_result)
    monkeypatch.setattr(ts, "query_kubecost_allocation", _kubecost_result)

    result = ts.top_spenders(provider="all", limit=5, window="7d")
    json.dumps(result)

    assert result["status"] == "success"
    assert result["provider"] == "all"
    assert result["limit"] == 5
    assert set(result["providers"].keys()) == {"aws", "opencost", "kubecost"}
    # Ranked by total_cost desc.
    names = [row["name"] for row in result["top_spenders"]]
    assert names[0] == "AmazonEC2"  # 80
    assert "acme-web" in names
    assert all("total_cost" in row for row in result["top_spenders"])


def test_top_spenders_limit_applied(monkeypatch):
    monkeypatch.setattr(ts, "query_aws_costs", _aws_result)
    monkeypatch.setattr(ts, "query_opencost_allocation", _opencost_result)
    monkeypatch.setattr(ts, "query_kubecost_allocation", _kubecost_result)

    result = ts.top_spenders(provider="all", limit=2)
    assert len(result["top_spenders"]) == 2


def test_top_spenders_single_provider(monkeypatch):
    monkeypatch.setattr(ts, "query_aws_costs", _aws_result)
    monkeypatch.setattr(ts, "query_opencost_allocation", _unavailable)
    monkeypatch.setattr(ts, "query_kubecost_allocation", _unavailable)

    result = ts.top_spenders(provider="aws")
    assert result["status"] == "success"
    # Only AWS ran.
    assert set(result["providers"].keys()) == {"aws"}
    assert all(row["provider"] == "aws" for row in result["top_spenders"])


def test_top_spenders_all_providers_unavailable(monkeypatch):
    monkeypatch.setattr(ts, "query_aws_costs", _unavailable)
    monkeypatch.setattr(ts, "query_opencost_allocation", _unavailable)
    monkeypatch.setattr(ts, "query_kubecost_allocation", _unavailable)

    result = ts.top_spenders(provider="all")
    assert result["status"] == "unavailable"
    assert result["top_spenders"] == []
    # But per-provider reports must still explain why.
    assert all(
        p.get("status") == "unavailable" for p in result["providers"].values()
    )


def test_window_translation_to_dates():
    start, end = ts._window_to_dates("7d")
    assert len(start) == 10 and start.count("-") == 2
    assert len(end) == 10 and end.count("-") == 2
    assert start < end


def test_window_translation_hour():
    days = ts._window_to_days("24h")
    assert days == 1
    days = ts._window_to_days("48h")
    assert days == 2


def test_window_translation_fallback():
    # Unparseable window defaults to 7 days.
    assert ts._window_to_days("gibberish") == 7
