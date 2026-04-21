"""Tests for :class:`connectors.log_fetcher.LogFetcher`."""

from __future__ import annotations

from datetime import datetime, timedelta

import httpx
import pytest

from connectors.log_fetcher import LogFetcher
from connectors.signoz_client import SigNozClient


pytestmark = pytest.mark.asyncio


def _client(handler) -> SigNozClient:
    return SigNozClient(
        base_url="http://signoz.test",
        api_key=None,
        retry_attempts=1,
        transport=httpx.MockTransport(handler),
    )


async def test_search_rejects_non_positive_limit() -> None:
    async with _client(lambda r: httpx.Response(200, json={})) as client:
        with pytest.raises(ValueError):
            await LogFetcher(client).search(
                "x", datetime(2026, 1, 1), datetime(2026, 1, 2), limit=0
            )


async def test_search_rejects_reversed_range() -> None:
    async with _client(lambda r: httpx.Response(200, json={})) as client:
        with pytest.raises(ValueError):
            await LogFetcher(client).search(
                "x", datetime(2026, 1, 2), datetime(2026, 1, 1)
            )


async def test_search_parses_modern_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/logs"
        # Time range is forwarded as nanoseconds.
        start = int(request.url.params["start"])
        end = int(request.url.params["end"])
        assert end > start > 1_000_000_000_000_000_000
        return httpx.Response(
            200,
            json={
                "data": {
                    "logs": [
                        {
                            "timestamp": 1_700_000_000_000_000_000,
                            "body": "hello",
                            "severity_text": "INFO",
                            "service": "gateway",
                            "trace_id": "t1",
                        }
                    ],
                    "next_page": None,
                }
            },
        )

    async with _client(handler) as client:
        entries = await LogFetcher(client).search(
            "level=info",
            datetime(2026, 1, 1),
            datetime(2026, 1, 2),
            limit=10,
        )

    assert len(entries) == 1
    entry = entries[0]
    assert entry.body == "hello"
    assert entry.severity == "INFO"
    assert entry.service == "gateway"
    assert entry.trace_id == "t1"


async def test_pagination_follows_next_page_until_limit() -> None:
    pages = {
        None: {
            "data": {
                "logs": [
                    {"timestamp": 1_700_000_000_000_000_000, "body": "A"},
                    {"timestamp": 1_700_000_000_100_000_000, "body": "B"},
                ],
                "next_page": "p2",
            }
        },
        "p2": {
            "data": {
                "logs": [
                    {"timestamp": 1_700_000_000_200_000_000, "body": "C"},
                    {"timestamp": 1_700_000_000_300_000_000, "body": "D"},
                ],
                "next_page": "p3",
            }
        },
        "p3": {
            "data": {
                "logs": [
                    {"timestamp": 1_700_000_000_400_000_000, "body": "E"},
                ],
                "next_page": None,
            }
        },
    }

    seen_pages: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        page = request.url.params.get("page")
        seen_pages.append(page)
        return httpx.Response(200, json=pages[page])

    async with _client(handler) as client:
        entries = await LogFetcher(client).search(
            "q", datetime(2026, 1, 1), datetime(2026, 1, 2), limit=4
        )

    # Pagination stops once limit is reached; 3rd page shouldn't be fetched.
    assert [e.body for e in entries] == ["A", "B", "C", "D"]
    assert seen_pages == [None, "p2"]


async def test_search_handles_legacy_result_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "result": [
                    {
                        "list": [
                            {
                                "timestamp": "2026-04-01T00:00:00Z",
                                "message": "legacy",
                                "level": "WARN",
                            }
                        ]
                    }
                ]
            },
        )

    async with _client(handler) as client:
        entries = await LogFetcher(client).search(
            "q",
            datetime(2026, 1, 1),
            datetime(2026, 1, 2),
            limit=10,
        )

    assert len(entries) == 1
    assert entries[0].body == "legacy"
    assert entries[0].severity == "WARN"


async def test_stops_when_next_page_missing() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={"data": {"logs": [{"timestamp": 1_700_000_000_000_000_000, "body": "x"}], "next_page": None}},
        )

    async with _client(handler) as client:
        entries = await LogFetcher(client).search(
            "q",
            datetime(2026, 1, 1),
            datetime(2026, 1, 1) + timedelta(hours=1),
            limit=100,
        )

    assert len(entries) == 1
    assert calls == 1
