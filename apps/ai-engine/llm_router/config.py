"""Configuration for the Aegis Local LLM Router (Layer 0.4).

The LLM router decides whether a given prompt is sent to a local Ollama
model (for sensitive/real-prod data) or to Claude API (for sanitized or
public content). This module defines the Pydantic configuration model
used to tune that behavior.

Design goals
------------
* Safe defaults: sensitive prompts route **local**, not cloud.
* Auditable: every field corresponds to a deployment-relevant decision
  (regulated-only mode, auto-detection toggle, sensitive backend, etc.).
* Zero surprises: unknown models or URLs should be obvious in logs —
  values flow straight through to the backends without translation.

The config can be embedded in the larger ``Settings`` object under an
``AEGIS_LLM_ROUTER_*`` prefix, or instantiated directly for tests.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Backend = Literal["ollama", "claude"]


class LLMRouterConfig(BaseModel):
    """Runtime configuration for the LLM router.

    Attributes:
        sensitive_backend: Backend to use when a prompt is classified as
            sensitive. Default ``"ollama"`` — keep real prod data on-prem.
        sanitized_backend: Backend to use when a prompt is classified as
            sanitized or public. Default ``"claude"`` — the smart remote
            model is appropriate for non-sensitive content.
        ollama_url: Base URL of the local Ollama HTTP API. Default is
            the Ollama default of ``http://localhost:11434``.
        ollama_model: Ollama model tag to use. Operators commonly pick
            ``llama3.1`` or ``gemma3:4b`` depending on hardware.
        claude_model: Anthropic model identifier. Defaults to the current
            Aegis target model.
        auto_detect_sensitive: When ``True`` the router classifies every
            prompt via :mod:`llm_router.sensitivity`. When ``False`` only
            explicit overrides matter — all traffic goes to
            ``sanitized_backend`` unless overridden.
        always_local: Regulated-deployment kill-switch. When ``True`` the
            router ignores classification and sends every call to the
            local backend. Intended for PIPA-restricted tenants where
            cross-border transfer is never permitted.
        sensitive_keywords: Extra deployment-specific keywords (company
            names, product names, internal codewords) that should force
            a prompt to be classified sensitive. Matched case-insensitively
            as substrings.
        fallback_to_cloud_on_local_failure: When ``True`` and the local
            backend is unreachable, the router falls back to cloud with
            a warning. **Default is ``False``** — a silent cross-border
            leak is a worse failure mode than a loud 503.
    """

    sensitive_backend: Backend = "ollama"
    sanitized_backend: Backend = "claude"

    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    claude_model: str = "claude-opus-4-7"

    auto_detect_sensitive: bool = True
    always_local: bool = False

    sensitive_keywords: list[str] = Field(default_factory=list)

    fallback_to_cloud_on_local_failure: bool = False

    # Request tuning
    max_tokens: int = 2048
    temperature: float = 0.3
    request_timeout_s: float = 120.0
