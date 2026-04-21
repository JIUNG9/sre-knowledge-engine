"""Tests for the LLMRouter orchestration layer."""

from __future__ import annotations

import pytest

from llm_router import (
    LLMRouter,
    LLMRouterConfig,
    OllamaUnavailable,
    RouterResponse,
)


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #


class _FakeBackend:
    """Minimal duck-typed backend used for routing tests."""

    def __init__(self, name: str, *, raise_unavailable: bool = False):
        self.name = name
        self.raise_unavailable = raise_unavailable
        self.calls: list[list[dict]] = []
        self.model = f"{name}-model"

    async def complete(self, messages):
        if self.raise_unavailable:
            raise OllamaUnavailable("fake unavailable")
        self.calls.append(messages)
        return RouterResponse(
            text=f"reply from {self.name}",
            backend=self.name,
            model=self.model,
        )

    async def stream(self, messages):
        if self.raise_unavailable:
            raise OllamaUnavailable("fake unavailable")
        self.calls.append(messages)
        for piece in ("hello from ", self.name):
            yield piece


def _mk_router(**config_overrides):
    config = LLMRouterConfig(**config_overrides)
    claude = _FakeBackend("claude")
    ollama = _FakeBackend("ollama")
    router = LLMRouter(
        config=config, claude_backend=claude, ollama_backend=ollama
    )
    return router, claude, ollama


# --------------------------------------------------------------------------- #
# Auto-detect
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_sanitized_prompt_goes_to_claude() -> None:
    router, claude, ollama = _mk_router()
    resp = await router.complete(
        [{"role": "user", "content": "what is kubernetes?"}]
    )
    assert resp.backend == "claude"
    assert len(claude.calls) == 1
    assert len(ollama.calls) == 0
    assert resp.decision is not None
    assert resp.decision.backend == "claude"


@pytest.mark.asyncio
async def test_sensitive_prompt_goes_to_ollama() -> None:
    router, claude, ollama = _mk_router()
    resp = await router.complete(
        [{
            "role": "user",
            "content": "Pod user-service-7fbd4c9f-xk2ps on prod.api.acme-corp.com OOM-killed",
        }]
    )
    assert resp.backend == "ollama"
    assert len(ollama.calls) == 1
    assert len(claude.calls) == 0


# --------------------------------------------------------------------------- #
# Explicit mode overrides
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_mode_local_forces_ollama_even_for_public_question() -> None:
    router, claude, ollama = _mk_router()
    resp = await router.complete(
        [{"role": "user", "content": "what is TCP?"}],
        mode="local",
    )
    assert resp.backend == "ollama"
    assert resp.decision.override == "explicit_local"


@pytest.mark.asyncio
async def test_mode_cloud_forces_claude_even_for_sensitive_prompt() -> None:
    router, claude, ollama = _mk_router()
    resp = await router.complete(
        [{"role": "user", "content": "user@realco.com logged in from 52.1.2.3"}],
        mode="cloud",
    )
    assert resp.backend == "claude"
    assert resp.decision.override == "explicit_cloud"


# --------------------------------------------------------------------------- #
# Always-local kill switch
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_always_local_routes_everything_to_ollama() -> None:
    router, claude, ollama = _mk_router(always_local=True)
    for msg in [
        "what is kubernetes?",
        "generic hello",
        "real email user@company.co.kr",
    ]:
        await router.complete([{"role": "user", "content": msg}])
    assert len(ollama.calls) == 3
    assert len(claude.calls) == 0


# --------------------------------------------------------------------------- #
# Sensitivity override
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_sensitivity_override_true_forces_local() -> None:
    router, claude, ollama = _mk_router()
    await router.complete(
        [{"role": "user", "content": "a truly harmless string"}],
        sensitivity_override=True,
    )
    assert len(ollama.calls) == 1
    assert len(claude.calls) == 0


@pytest.mark.asyncio
async def test_sensitivity_override_false_forces_cloud() -> None:
    router, claude, ollama = _mk_router()
    await router.complete(
        [{"role": "user", "content": "user@realco.com logged in from 52.1.2.3"}],
        sensitivity_override=False,
    )
    assert len(claude.calls) == 1
    assert len(ollama.calls) == 0


# --------------------------------------------------------------------------- #
# Auto-detect disabled
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_auto_detect_disabled_sends_to_sanitized_backend() -> None:
    router, claude, ollama = _mk_router(auto_detect_sensitive=False)
    # Sensitive-looking content but auto-detect is off -> cloud
    await router.complete(
        [{"role": "user", "content": "user@realco.com 52.1.2.3 arn:aws:iam::123456789012:role/x"}]
    )
    assert len(claude.calls) == 1
    assert len(ollama.calls) == 0


# --------------------------------------------------------------------------- #
# Fallback behavior
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_ollama_unavailable_fails_loudly_by_default() -> None:
    config = LLMRouterConfig()
    claude = _FakeBackend("claude")
    ollama = _FakeBackend("ollama", raise_unavailable=True)
    router = LLMRouter(config=config, claude_backend=claude, ollama_backend=ollama)

    with pytest.raises(OllamaUnavailable):
        await router.complete(
            [{"role": "user", "content": "user@realco.com pod-abc123-xx99 OOM"}]
        )
    assert len(claude.calls) == 0  # must NOT leak cross-border


@pytest.mark.asyncio
async def test_ollama_unavailable_falls_back_when_configured() -> None:
    config = LLMRouterConfig(fallback_to_cloud_on_local_failure=True)
    claude = _FakeBackend("claude")
    ollama = _FakeBackend("ollama", raise_unavailable=True)
    router = LLMRouter(config=config, claude_backend=claude, ollama_backend=ollama)

    resp = await router.complete(
        [{"role": "user", "content": "user@realco.com OOM"}]
    )
    assert resp.backend == "claude"
    assert resp.decision.override == "fallback_to_cloud"
    assert len(claude.calls) == 1


# --------------------------------------------------------------------------- #
# Streaming
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_stream_routes_like_complete() -> None:
    router, claude, ollama = _mk_router()
    chunks = []
    async for c in router.stream(
        [{"role": "user", "content": "what is kubernetes?"}]
    ):
        chunks.append(c)
    assert "".join(chunks) == "hello from claude"
    assert len(claude.calls) == 1


# --------------------------------------------------------------------------- #
# Decision explanation
# --------------------------------------------------------------------------- #


def test_decide_explains_signals() -> None:
    router, _, _ = _mk_router(sensitive_keywords=["acme-corp"])
    d = router.decide(
        [{"role": "user", "content": "acme-corp prod is down"}]
    )
    assert d.backend == "ollama"
    assert d.sensitivity is not None
    assert any("keyword:acme-corp" in s for s in d.sensitivity.signals)
