"""Tests for :class:`connectors.alert_fetcher.AlertFetcher`."""

from __future__ import annotations

from datetime import datetime, timedelta

import httpx
import pytest

from connectors.alert_fetcher import AlertFetcher
from connectors.signoz_client import SigNozClient


pytestmark = pytest.mark.asyncio


def _client(handler) -> SigNozClient:
    return SigNozClient(
        base_url="http://signoz.test",
        api_key=None,
        retry_attempts=1,
        transport=httpx.MockTransport(handler),
    )


async def test_list_rules() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/rules"
        return httpx.Response(
            200,
            json={
                "data": {
                    "rules": [
                        {
                            "id": "r1",
                            "name": "High 5xx",
                            "severity": "critical",
                            "state": "firing",
                            "expr": 'rate(errors[5m]) > 0.05',
                            "labels": {"team": "sre"},
                        },
                        {
                            "id": "r2",
                            "name": "Memory",
                            "state": "inactive",
                        },
                    ]
                }
            },
        )

    async with _client(handler) as client:
        rules = await AlertFetcher(client).list_rules()

    assert [r.id for r in rules] == ["r1", "r2"]
    assert rules[0].severity == "critical"
    assert rules[0].state == "firing"
    assert rules[1].state == "inactive"


async def test_list_alerts_filters_firing() -> None:
    seen_params: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_params.update(dict(request.url.params))
        return httpx.Response(
            200,
            json={
                "data": {
                    "alerts": [
                        {
                            "ruleId": "r1",
                            "ruleName": "High 5xx",
                            "state": "firing",
                            "value": 0.1,
                            "firedAt": 1_700_000_000_000,
                        },
                        {
                            "ruleId": "r2",
                            "ruleName": "Memory",
                            "state": "resolved",
                            "firedAt": 1_700_000_000_000,
                            "resolvedAt": 1_700_000_100_000,
                        },
                    ]
                }
            },
        )

    async with _client(handler) as client:
        firing = await AlertFetcher(client).list_alerts(state="firing")

    assert seen_params.get("state") == "firing"
    assert len(firing) == 1
    assert firing[0].rule_id == "r1"
    assert firing[0].state == "firing"


async def test_list_alerts_no_filter_returns_all() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "state" not in request.url.params
        return httpx.Response(
            200,
            json={
                "data": {
                    "alerts": [
                        {
                            "ruleId": "r1",
                            "ruleName": "x",
                            "state": "firing",
                            "firedAt": 1_700_000_000_000,
                        },
                        {
                            "ruleId": "r2",
                            "ruleName": "y",
                            "state": "resolved",
                            "firedAt": 1_700_000_000_000,
                            "resolvedAt": 1_700_000_100_000,
                        },
                    ]
                }
            },
        )

    async with _client(handler) as client:
        events = await AlertFetcher(client).list_alerts()

    assert len(events) == 2


async def test_get_alert_history() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/rules/r1/history"
        assert "start" in request.url.params
        assert "end" in request.url.params
        return httpx.Response(
            200,
            json={
                "data": {
                    "history": [
                        {
                            "ruleId": "r1",
                            "ruleName": "High 5xx",
                            "state": "firing",
                            "firedAt": 1_700_000_000_000,
                            "resolvedAt": 1_700_000_100_000,
                        }
                    ]
                }
            },
        )

    start = datetime(2026, 1, 1)
    end = start + timedelta(hours=1)
    async with _client(handler) as client:
        events = await AlertFetcher(client).get_alert_history("r1", start, end)

    assert len(events) == 1
    assert events[0].rule_id == "r1"
    assert events[0].state == "firing"
    assert events[0].resolved_at is not None


async def test_get_alert_history_rejects_bad_inputs() -> None:
    async with _client(lambda r: httpx.Response(200, json={})) as client:
        with pytest.raises(ValueError):
            await AlertFetcher(client).get_alert_history(
                "", datetime(2026, 1, 1), datetime(2026, 1, 2)
            )
        with pytest.raises(ValueError):
            await AlertFetcher(client).get_alert_history(
                "r1", datetime(2026, 1, 2), datetime(2026, 1, 1)
            )
