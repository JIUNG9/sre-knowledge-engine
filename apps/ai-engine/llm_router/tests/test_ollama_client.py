"""Tests for the Ollama HTTP backend.

We mock the httpx transport rather than talking to a live daemon so
the test suite runs in CI without Ollama installed.
"""

from __future__ import annotations

import json

import httpx
import pytest

from llm_router.backends.ollama import OllamaBackend, OllamaUnavailable


def _mock_transport(handler):
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_complete_parses_ollama_response(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        payload = json.loads(request.content.decode())
        assert payload["model"] == "llama3.1"
        assert payload["stream"] is False
        return httpx.Response(
            200,
            json={
                "model": "llama3.1",
                "message": {"role": "assistant", "content": "hello from local"},
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 12,
                "eval_count": 34,
                "total_duration": 123456789,
            },
        )

    # Monkey-patch httpx.AsyncClient to use our transport
    real_client = httpx.AsyncClient

    def _patched_client(*args, **kwargs):
        kwargs["transport"] = _mock_transport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr("llm_router.backends.ollama.httpx.AsyncClient", _patched_client)

    backend = OllamaBackend(model="llama3.1")
    resp = await backend.complete([{"role": "user", "content": "hi"}])

    assert resp.text == "hello from local"
    assert resp.backend == "ollama"
    assert resp.model == "llama3.1"
    assert resp.usage["prompt_eval_count"] == 12
    assert resp.usage["eval_count"] == 34
    assert resp.finish_reason == "stop"


@pytest.mark.asyncio
async def test_complete_raises_on_connect_error(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("nope")

    real_client = httpx.AsyncClient

    def _patched_client(*args, **kwargs):
        kwargs["transport"] = _mock_transport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr("llm_router.backends.ollama.httpx.AsyncClient", _patched_client)

    backend = OllamaBackend()
    with pytest.raises(OllamaUnavailable):
        await backend.complete([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_complete_raises_on_404_missing_model(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model not found"})

    real_client = httpx.AsyncClient

    def _patched_client(*args, **kwargs):
        kwargs["transport"] = _mock_transport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr("llm_router.backends.ollama.httpx.AsyncClient", _patched_client)

    backend = OllamaBackend(model="does-not-exist")
    with pytest.raises(OllamaUnavailable) as exc:
        await backend.complete([{"role": "user", "content": "hi"}])
    assert "does-not-exist" in str(exc.value) or "not installed" in str(exc.value)


@pytest.mark.asyncio
async def test_stream_yields_content_deltas(monkeypatch) -> None:
    chunks = [
        {"message": {"content": "hello "}, "done": False},
        {"message": {"content": "world"}, "done": False},
        {"message": {"content": "!"}, "done": True, "done_reason": "stop"},
    ]
    body = "\n".join(json.dumps(c) for c in chunks).encode()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body)

    real_client = httpx.AsyncClient

    def _patched_client(*args, **kwargs):
        kwargs["transport"] = _mock_transport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr("llm_router.backends.ollama.httpx.AsyncClient", _patched_client)

    backend = OllamaBackend()
    out = []
    async for piece in backend.stream([{"role": "user", "content": "hi"}]):
        out.append(piece)
    assert "".join(out) == "hello world!"


@pytest.mark.asyncio
async def test_health_returns_true_when_tags_ok(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags"
        return httpx.Response(200, json={"models": []})

    real_client = httpx.AsyncClient

    def _patched_client(*args, **kwargs):
        kwargs["transport"] = _mock_transport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr("llm_router.backends.ollama.httpx.AsyncClient", _patched_client)

    backend = OllamaBackend()
    assert await backend.health() is True


@pytest.mark.asyncio
async def test_health_returns_false_on_network_error(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("nope")

    real_client = httpx.AsyncClient

    def _patched_client(*args, **kwargs):
        kwargs["transport"] = _mock_transport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr("llm_router.backends.ollama.httpx.AsyncClient", _patched_client)

    backend = OllamaBackend()
    assert await backend.health() is False
