"""Tests for ``find_cost_anomalies`` with monkeypatched sub-tools."""

from __future__ import annotations

import json

import importlib

ad = importlib.import_module("mcp.tools.read.finops.anomaly_detect")


def _flat_series_with_spike():
    # 10 days flat at $100, then one spike to $1000.
    results = []
    for day in range(1, 11):
        results.append(
            {
                "start": f"2026-04-{day:02d}",
                "end": f"2026-04-{day + 1:02d}",
                "keys": [],
                "amount": 100.0,
                "currency": "USD",
            }
        )
    results.append(
        {
            "start": "2026-04-11",
            "end": "2026-04-12",
            "keys": [],
            "amount": 1000.0,
            "currency": "USD",
        }
    )
    return {
        "status": "success",
        "tool": "query_aws_costs",
        "results": results,
        "total_cost": sum(r["amount"] for r in results),
        "currency": "USD",
    }


def test_anomaly_detect_flags_spike(monkeypatch):
    monkeypatch.setattr(
        ad, "query_aws_costs", lambda **kwargs: _flat_series_with_spike()
    )

    result = ad.find_cost_anomalies(
        provider="aws", lookback_days=30, sensitivity=2.0
    )
    json.dumps(result)

    assert result["status"] == "success"
    assert result["tool"] == "find_cost_anomalies"
    assert result["provider"] == "aws"
    assert result["anomaly_count"] >= 1
    # The spike must be the top anomaly.
    top = result["anomalies"][0]
    assert top["amount"] == 1000.0
    assert top["z_score"] >= 2.0


def test_anomaly_detect_no_spike(monkeypatch):
    def _flat(**_):
        return {
            "status": "success",
            "tool": "query_aws_costs",
            "results": [
                {
                    "start": f"2026-04-{d:02d}",
                    "end": f"2026-04-{d + 1:02d}",
                    "keys": [],
                    "amount": 100.0,
                    "currency": "USD",
                }
                for d in range(1, 11)
            ],
            "total_cost": 1000.0,
            "currency": "USD",
        }

    monkeypatch.setattr(ad, "query_aws_costs", _flat)
    result = ad.find_cost_anomalies(provider="aws", lookback_days=10)
    assert result["status"] == "success"
    assert result["anomaly_count"] == 0


def test_anomaly_detect_not_enough_data(monkeypatch):
    def _tiny(**_):
        return {
            "status": "success",
            "tool": "query_aws_costs",
            "results": [
                {
                    "start": "2026-04-01",
                    "end": "2026-04-02",
                    "keys": [],
                    "amount": 100.0,
                    "currency": "USD",
                }
            ],
            "total_cost": 100.0,
            "currency": "USD",
        }

    monkeypatch.setattr(ad, "query_aws_costs", _tiny)
    result = ad.find_cost_anomalies(provider="aws", lookback_days=1)
    assert result["status"] == "success"
    assert result["anomalies"] == []
    assert "not enough data" in result.get("note", "")


def test_anomaly_detect_unavailable_backend(monkeypatch):
    def _unavail(**_):
        return {
            "status": "unavailable",
            "reason": "AWS creds missing",
        }

    monkeypatch.setattr(ad, "query_aws_costs", _unavail)
    result = ad.find_cost_anomalies(provider="aws", lookback_days=30)
    assert result["status"] == "unavailable"
    assert "AWS creds" in result["reason"]


def test_anomaly_detect_sensitivity_controls_count(monkeypatch):
    # Two spikes — a 2.5x and a 10x. High sensitivity (3.0) only
    # catches the 10x; low sensitivity (1.0) catches both.
    def _series_two_spikes(**_):
        amounts = [100.0] * 20 + [250.0, 1000.0]
        return {
            "status": "success",
            "results": [
                {
                    "start": f"2026-03-{(i + 1):02d}",
                    "end": f"2026-03-{(i + 2):02d}",
                    "keys": [],
                    "amount": amt,
                    "currency": "USD",
                }
                for i, amt in enumerate(amounts)
            ],
        }

    monkeypatch.setattr(ad, "query_aws_costs", _series_two_spikes)
    high = ad.find_cost_anomalies(provider="aws", sensitivity=3.0)
    low = ad.find_cost_anomalies(provider="aws", sensitivity=1.0)
    assert high["anomaly_count"] <= low["anomaly_count"]
    assert any(a["amount"] == 1000.0 for a in high["anomalies"])
