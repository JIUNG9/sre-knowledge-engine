"""Tests for :class:`connectors.metric_fetcher.MetricFetcher`."""

from __future__ import annotations

import math
from datetime import datetime, timedelta

import httpx
import pytest

from connectors.metric_fetcher import MetricFetcher
from connectors.signoz_client import SigNozClient


pytestmark = pytest.mark.asyncio


def _client(handler) -> SigNozClient:
    return SigNozClient(
        base_url="http://signoz.test",
        api_key=None,
        retry_attempts=1,
        transport=httpx.MockTransport(handler),
    )


async def test_query_range_forwards_params_and_parses_matrix() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/query_range"
        captured.update(dict(request.url.params))
        return httpx.Response(
            200,
            json={
                "status": "success",
                "data": {
                    "resultType": "matrix",
                    "result": [
                        {
                            "metric": {"service": "gateway"},
                            "values": [
                                [1_700_000_000, "0.5"],
                                [1_700_000_030, "0.7"],
                            ],
                        }
                    ],
                },
            },
        )

    start = datetime(2026, 1, 1)
    end = start + timedelta(minutes=1)
    async with _client(handler) as client:
        result = await MetricFetcher(client).query_range(
            'rate(http_requests_total[1m])',
            start=start,
            end=end,
            step_seconds=30,
        )

    assert captured["query"].startswith("rate(http_requests_total")
    assert int(captured["step"]) == 30
    assert len(result.series) == 1
    row = result.series[0]
    assert row.labels == {"service": "gateway"}
    assert len(row.points) == 2
    assert pytest.approx(row.points[0].value) == 0.5
    assert pytest.approx(row.points[1].value) == 0.7


async def test_query_range_rejects_bad_args() -> None:
    async def _noop(_: httpx.Request) -> httpx.Response:  # pragma: no cover
        return httpx.Response(200, json={})

    async with _client(_noop) as client:
        with pytest.raises(ValueError):
            await MetricFetcher(client).query_range(
                "up", datetime(2026, 1, 1), datetime(2026, 1, 1), step_seconds=0
            )
        with pytest.raises(ValueError):
            await MetricFetcher(client).query_range(
                "up",
                datetime(2026, 1, 2),
                datetime(2026, 1, 1),
                step_seconds=10,
            )


async def test_query_instant_returns_last_point() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "status": "success",
                "data": {
                    "resultType": "matrix",
                    "result": [
                        {
                            "metric": {"service": "gateway"},
                            "values": [[1_700_000_000, "1.5"]],
                        }
                    ],
                },
            },
        )

    async with _client(handler) as client:
        point = await MetricFetcher(client).query_instant(
            "up", datetime(2026, 1, 1)
        )

    assert pytest.approx(point.value) == 1.5
    assert point.labels == {"service": "gateway"}


async def test_query_instant_on_empty_result_returns_nan() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"status": "success", "data": {"resultType": "matrix", "result": []}},
        )

    async with _client(handler) as client:
        point = await MetricFetcher(client).query_instant(
            "up", datetime(2026, 1, 1)
        )

    assert math.isnan(point.value)


async def test_parses_signoz_native_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "result": [
                    {
                        "series": [
                            {
                                "labels": {"svc": "api"},
                                "values": [
                                    {"timestamp": 1_700_000_000_000, "value": 2},
                                    {"timestamp": 1_700_000_030_000, "value": 3},
                                ],
                            }
                        ]
                    }
                ]
            },
        )

    async with _client(handler) as client:
        result = await MetricFetcher(client).query_range(
            "sum(up)",
            start=datetime(2026, 1, 1),
            end=datetime(2026, 1, 1) + timedelta(minutes=1),
            step_seconds=30,
        )

    assert len(result.series) == 1
    row = result.series[0]
    assert row.labels == {"svc": "api"}
    assert [p.value for p in row.points] == [2.0, 3.0]
