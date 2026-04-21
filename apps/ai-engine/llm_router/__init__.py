"""Aegis Local LLM Router (Layer 0.4).

Public API for routing LLM calls between a local Ollama model and the
Claude API based on prompt sensitivity. The router exists to prevent
cross-border transfer of real production data — a hard requirement
under the Korean PIPA Sep-2026 amendment.

Typical usage::

    from llm_router import LLMRouter, LLMRouterConfig

    router = LLMRouter(
        config=LLMRouterConfig(sensitive_keywords=["acme-corp", "customer-xyz"]),
    )

    # Auto-classify:
    resp = await router.complete(
        [{"role": "user", "content": "what is kubernetes?"}]
    )
    assert resp.backend == "claude"

    # Explicit local:
    resp = await router.complete(messages, mode="local")

    # Regulated deployment:
    router = LLMRouter(config=LLMRouterConfig(always_local=True))

See ``README.md`` in this package for the full decision tree.
"""

from __future__ import annotations

from .backends import ClaudeBackend, OllamaBackend, OllamaUnavailable
from .config import LLMRouterConfig
from .router import LLMBackend, LLMRouter, RouterResponse, RoutingDecision
from .sensitivity import Sensitivity, classify_sensitivity

__all__ = [
    "LLMRouter",
    "LLMRouterConfig",
    "LLMBackend",
    "RouterResponse",
    "RoutingDecision",
    "Sensitivity",
    "classify_sensitivity",
    "ClaudeBackend",
    "OllamaBackend",
    "OllamaUnavailable",
]
