"""Tests for :class:`connectors.trace_fetcher.TraceFetcher`."""

from __future__ import annotations

from datetime import datetime, timedelta

import httpx
import pytest

from connectors.signoz_client import SigNozClient
from connectors.trace_fetcher import TraceFetcher


pytestmark = pytest.mark.asyncio


def _client(handler) -> SigNozClient:
    return SigNozClient(
        base_url="http://signoz.test",
        api_key=None,
        retry_attempts=1,
        transport=httpx.MockTransport(handler),
    )


async def test_get_trace_parses_spans() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/traces/abc"
        return httpx.Response(
            200,
            json={
                "data": {
                    "traceId": "abc",
                    "rootService": "gateway",
                    "rootOperation": "GET /",
                    "startTime": 1_700_000_000_000_000_000,
                    "durationMs": 42.0,
                    "spans": [
                        {
                            "spanId": "s1",
                            "parentSpanId": None,
                            "name": "GET /",
                            "serviceName": "gateway",
                            "startTime": 1_700_000_000_000_000_000,
                            "durationMs": 42.0,
                            "statusCode": "OK",
                        },
                        {
                            "spanId": "s2",
                            "parentSpanId": "s1",
                            "name": "db.query",
                            "serviceName": "postgres",
                            "startTime": 1_700_000_000_100_000_000,
                            "durationMs": 12.5,
                            "statusCode": "OK",
                        },
                    ],
                }
            },
        )

    async with _client(handler) as client:
        trace = await TraceFetcher(client).get_trace("abc")

    assert trace.trace_id == "abc"
    assert trace.root_service == "gateway"
    assert len(trace.spans) == 2
    assert trace.spans[1].parent_span_id == "s1"
    assert trace.spans[1].service == "postgres"


async def test_get_trace_rejects_empty_id() -> None:
    async with _client(lambda r: httpx.Response(200, json={})) as client:
        with pytest.raises(ValueError):
            await TraceFetcher(client).get_trace("")


async def test_search_forwards_filters_and_parses_summaries() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(dict(request.url.params))
        return httpx.Response(
            200,
            json={
                "data": {
                    "traces": [
                        {
                            "traceId": "t1",
                            "serviceName": "gateway",
                            "operation": "GET /",
                            "startTime": 1_700_000_000_000_000_000,
                            "durationMs": 42.0,
                            "statusCode": "OK",
                            "spanCount": 3,
                        },
                        {
                            "traceId": "t2",
                            "serviceName": "gateway",
                            "operation": "POST /login",
                            "startTime": 1_700_000_100_000_000_000,
                            "durationMs": 101.2,
                            "statusCode": "ERROR",
                            "spanCount": 7,
                        },
                    ]
                }
            },
        )

    start = datetime(2026, 1, 1)
    end = start + timedelta(hours=1)
    async with _client(handler) as client:
        summaries = await TraceFetcher(client).search(
            service="gateway",
            operation="POST /login",
            min_duration_ms=100,
            start=start,
            end=end,
        )

    assert captured["service"] == "gateway"
    assert captured["operation"] == "POST /login"
    assert int(captured["minDuration"]) == 100
    assert len(summaries) == 2
    assert summaries[0].trace_id == "t1"
    assert summaries[1].status_code == "ERROR"


async def test_search_rejects_bad_range() -> None:
    async with _client(lambda r: httpx.Response(200, json={})) as client:
        with pytest.raises(ValueError):
            await TraceFetcher(client).search(
                service=None,
                operation=None,
                min_duration_ms=None,
                start=datetime(2026, 1, 2),
                end=datetime(2026, 1, 1),
            )


async def test_search_rejects_negative_min_duration() -> None:
    async with _client(lambda r: httpx.Response(200, json={})) as client:
        with pytest.raises(ValueError):
            await TraceFetcher(client).search(
                service=None,
                operation=None,
                min_duration_ms=-5,
                start=datetime(2026, 1, 1),
                end=datetime(2026, 1, 2),
            )
