"""Tests for :class:`connectors.signoz_client.SigNozClient`.

We install a :class:`httpx.MockTransport` at client-construction time,
so no real network activity is possible.
"""

from __future__ import annotations

import httpx
import pytest

from connectors.signoz_client import SigNozClient, SigNozError


pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _client(handler, **overrides) -> SigNozClient:
    transport = httpx.MockTransport(handler)
    kwargs = {
        "base_url": "http://signoz.test",
        "api_key": "secret",
        "verify_tls": False,
        "timeout_seconds": 5,
        "retry_attempts": 3,
        "transport": transport,
    }
    kwargs.update(overrides)
    return SigNozClient(**kwargs)


# --------------------------------------------------------------------------- #
# Happy path
# --------------------------------------------------------------------------- #


async def test_bearer_auth_is_sent() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers.get("authorization", ""))
        return httpx.Response(200, json={"ok": True})

    async with _client(handler) as client:
        data = await client.get("/api/v1/rules")

    assert data == {"ok": True}
    assert seen == ["Bearer secret"]


async def test_no_auth_header_when_api_key_missing() -> None:
    seen: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers.get("authorization"))
        return httpx.Response(200, json={"ok": True})

    async with _client(handler, api_key=None) as client:
        await client.get("/api/v1/rules")

    assert seen == [None]


async def test_post_forwards_json_body() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content.decode()
        return httpx.Response(200, json={"received": True})

    async with _client(handler) as client:
        await client.post("/api/v1/echo", json={"hello": "world"})

    assert '"hello"' in captured["body"]
    assert "world" in captured["body"]


# --------------------------------------------------------------------------- #
# Error paths
# --------------------------------------------------------------------------- #


async def test_401_is_surfaced_as_signoz_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "nope"})

    async with _client(handler) as client:
        with pytest.raises(SigNozError) as excinfo:
            await client.get("/api/v1/rules")

    err = excinfo.value
    assert err.status_code == 401
    assert err.method == "GET"
    assert "/api/v1/rules" in err.url
    assert "nope" in err.body
    assert err.request_id


async def test_4xx_is_not_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(400, json={"error": "bad request"})

    async with _client(handler) as client:
        with pytest.raises(SigNozError):
            await client.get("/api/v1/logs")

    assert calls == 1


async def test_5xx_is_retried_then_succeeds() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls < 3:
            return httpx.Response(503, json={"error": "overloaded"})
        return httpx.Response(200, json={"ok": True})

    async with _client(handler) as client:
        data = await client.get("/api/v1/logs")

    assert data == {"ok": True}
    assert calls == 3


async def test_5xx_exhausts_retries_and_raises() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(502, text="bad gateway")

    async with _client(handler) as client:
        with pytest.raises(SigNozError) as excinfo:
            await client.get("/api/v1/logs")

    assert calls == 3
    assert excinfo.value.status_code == 502
    assert "bad gateway" in excinfo.value.body


async def test_transport_error_is_retried_then_normalised() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("boom", request=request)

    async with _client(handler) as client:
        with pytest.raises(SigNozError) as excinfo:
            await client.get("/api/v1/logs")

    assert calls == 3
    assert excinfo.value.status_code == 0
    assert "boom" in str(excinfo.value)


async def test_timeout_is_normalised() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    async with _client(handler, retry_attempts=1) as client:
        with pytest.raises(SigNozError) as excinfo:
            await client.get("/api/v1/logs")

    assert excinfo.value.status_code == 0
    assert "slow" in str(excinfo.value)


async def test_retry_attempts_must_be_positive() -> None:
    with pytest.raises(ValueError):
        SigNozClient(base_url="http://x", retry_attempts=0)
