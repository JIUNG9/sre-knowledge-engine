"""Aegis Local LLM Router — Layer 0.4.

Routes every LLM call to either:

1. A **local Ollama** model when the prompt contains real production data
   (PIPA-protected under the Sep-2026 Korean amendment), or
2. **Claude API** when the prompt is sanitized/synthetic/public.

The router is the only place in Aegis that talks to an LLM. Every other
agent (analyzer, investigator, remediator, wiki synthesizer) should go
through :class:`LLMRouter` so decisions are centralized and auditable.

Routing decision tree::

    prompt
      │
      ├── config.always_local == True  ─────────────────────── OLLAMA
      │
      ├── mode == "local"              ─────────────────────── OLLAMA
      │
      ├── mode == "cloud"              ─────────────────────── CLAUDE
      │
      ├── sensitivity_override given   ─── sensitive?  ─── yes ─── OLLAMA
      │                                                   no  ─── CLAUDE
      │
      ├── config.auto_detect == True ─── classify_sensitivity(text)
      │                                      │
      │                                      ├── sensitive  ─── OLLAMA
      │                                      ├── borderline ─── OLLAMA (safe default)
      │                                      └── sanitized  ─── CLAUDE
      │
      └── otherwise                    ─────────────────────── CLAUDE

Every decision is logged at INFO with its driving signals for audit.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Literal

from .backends import ClaudeBackend, OllamaBackend, OllamaUnavailable
from .config import LLMRouterConfig
from .sensitivity import Sensitivity, classify_sensitivity


logger = logging.getLogger("aegis.llm_router")


Mode = Literal["auto", "local", "cloud"]


# --------------------------------------------------------------------------- #
# Public types
# --------------------------------------------------------------------------- #


class LLMBackend:
    """Marker/base type for backends. Kept for ``isinstance`` + exports.

    Both :class:`llm_router.backends.ClaudeBackend` and
    :class:`llm_router.backends.OllamaBackend` implement the same
    duck-typed interface: ``.complete(messages)`` and ``.stream(messages)``.
    We don't force an ABC because the backends are intentionally thin
    wrappers and duck typing is sufficient.
    """


@dataclass
class RoutingDecision:
    """Why the router picked a given backend.

    This is returned alongside the response so callers (and audit logs)
    can explain exactly why a prompt went local vs. cloud.
    """

    backend: str
    mode: Mode
    reason: str
    sensitivity: Sensitivity | None = None
    override: str | None = None  # "always_local" | "explicit_local" | "explicit_cloud" | "sensitivity_override"


@dataclass
class RouterResponse:
    """Unified response from either backend.

    Backends normalize their native responses into this shape so the
    rest of Aegis doesn't need to know who served the request.
    """

    text: str
    backend: str
    model: str
    usage: dict[str, Any] = field(default_factory=dict)
    finish_reason: str | None = None
    decision: RoutingDecision | None = None


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #


class LLMRouter:
    """Central LLM dispatcher — sensitivity-aware routing.

    Example::

        router = LLMRouter(
            config=LLMRouterConfig(sensitive_keywords=["acme-corp", "customer-xyz"]),
        )
        resp = await router.complete(
            [{"role": "user", "content": "What is kubernetes?"}]
        )
        # resp.backend == "claude"

        resp = await router.complete(
            [{"role": "user", "content": "Pod user-svc-a1b2c3-x1y2 is OOM-killing"}]
        )
        # resp.backend == "ollama"
    """

    def __init__(
        self,
        config: LLMRouterConfig | None = None,
        claude_backend: Any | None = None,
        ollama_backend: Any | None = None,
    ):
        self.config = config or LLMRouterConfig()

        self.claude = claude_backend or ClaudeBackend(
            model=self.config.claude_model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            timeout_s=self.config.request_timeout_s,
        )
        self.ollama = ollama_backend or OllamaBackend(
            base_url=self.config.ollama_url,
            model=self.config.ollama_model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            timeout_s=self.config.request_timeout_s,
        )

    # ------------------------------------------------------------------ #
    # Decision
    # ------------------------------------------------------------------ #
    def _join_text(self, messages: list[dict]) -> str:
        pieces: list[str] = []
        for m in messages:
            content = m.get("content", "")
            if isinstance(content, str):
                pieces.append(content)
            elif isinstance(content, list):
                # Anthropic-style content blocks
                for block in content:
                    t = block.get("text") if isinstance(block, dict) else None
                    if t:
                        pieces.append(t)
        return "\n".join(pieces)

    def decide(
        self,
        messages: list[dict],
        mode: Mode = "auto",
        sensitivity_override: bool | None = None,
    ) -> RoutingDecision:
        """Compute a :class:`RoutingDecision` without executing the call.

        Useful for tests and for UI previews ("this prompt would go local
        because: hostname, email, aws_account_id").
        """
        # 1. Regulated deployments: always local.
        if self.config.always_local:
            return RoutingDecision(
                backend=self.config.sensitive_backend,
                mode=mode,
                reason="always_local flag set",
                override="always_local",
            )

        # 2. Explicit mode overrides classification.
        if mode == "local":
            return RoutingDecision(
                backend=self.config.sensitive_backend,
                mode=mode,
                reason="explicit mode=local",
                override="explicit_local",
            )
        if mode == "cloud":
            return RoutingDecision(
                backend=self.config.sanitized_backend,
                mode=mode,
                reason="explicit mode=cloud",
                override="explicit_cloud",
            )

        # 3. Per-call sensitivity override.
        if sensitivity_override is not None:
            backend = (
                self.config.sensitive_backend
                if sensitivity_override
                else self.config.sanitized_backend
            )
            return RoutingDecision(
                backend=backend,
                mode=mode,
                reason=f"sensitivity_override={sensitivity_override}",
                override="sensitivity_override",
            )

        # 4. Auto-detect.
        if self.config.auto_detect_sensitive:
            text = self._join_text(messages)
            sens = classify_sensitivity(
                text, extra_keywords=self.config.sensitive_keywords
            )
            backend = (
                self.config.sensitive_backend
                if sens.is_sensitive
                else self.config.sanitized_backend
            )
            return RoutingDecision(
                backend=backend,
                mode=mode,
                reason=f"auto-detect level={sens.level} signals={sens.signals}",
                sensitivity=sens,
            )

        # 5. Auto-detect disabled: default to sanitized backend (cloud).
        return RoutingDecision(
            backend=self.config.sanitized_backend,
            mode=mode,
            reason="auto_detect disabled — defaulting to sanitized_backend",
        )

    # ------------------------------------------------------------------ #
    # Execution helpers
    # ------------------------------------------------------------------ #
    def _backend_for(self, name: str):
        if name == "ollama":
            return self.ollama
        if name == "claude":
            return self.claude
        raise ValueError(f"Unknown backend: {name}")

    def _log_decision(self, decision: RoutingDecision) -> None:
        logger.info(
            "llm_router decision: backend=%s mode=%s reason=%s override=%s "
            "sensitivity_level=%s signals=%s",
            decision.backend,
            decision.mode,
            decision.reason,
            decision.override,
            decision.sensitivity.level if decision.sensitivity else None,
            decision.sensitivity.signals if decision.sensitivity else None,
        )

    async def _maybe_fallback(
        self,
        decision: RoutingDecision,
        exc: OllamaUnavailable,
    ) -> RoutingDecision:
        """Apply the cloud-fallback policy when Ollama is unreachable.

        Default: **fail loudly** (re-raise). This is the safer default
        for PIPA because silently falling back could leak prod data
        cross-border.

        If ``config.fallback_to_cloud_on_local_failure=True``, we warn
        and switch the decision to Claude.
        """
        if not self.config.fallback_to_cloud_on_local_failure:
            logger.error(
                "llm_router: local backend unreachable and fallback disabled — "
                "failing loudly to avoid cross-border leak: %s",
                exc,
            )
            raise exc

        logger.warning(
            "llm_router: local backend unreachable — falling back to cloud. "
            "THIS MAY TRANSFER SENSITIVE DATA CROSS-BORDER. reason=%s",
            exc,
        )
        return RoutingDecision(
            backend="claude",
            mode=decision.mode,
            reason=f"fallback_to_cloud after local failure: {exc}",
            sensitivity=decision.sensitivity,
            override="fallback_to_cloud",
        )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    async def complete(
        self,
        messages: list[dict],
        mode: Mode = "auto",
        sensitivity_override: bool | None = None,
    ) -> RouterResponse:
        """Route and execute a single completion.

        Args:
            messages: OpenAI/Anthropic-style ``[{role, content}]`` list.
            mode: ``"auto"`` (default, classify), ``"local"`` (force
                Ollama), or ``"cloud"`` (force Claude).
            sensitivity_override: When set, bypasses the classifier and
                routes as-if the prompt were sensitive (True) or
                sanitized (False).

        Returns:
            :class:`RouterResponse` with ``.decision`` attached.
        """
        decision = self.decide(messages, mode=mode, sensitivity_override=sensitivity_override)
        self._log_decision(decision)

        try:
            backend = self._backend_for(decision.backend)
            resp = await backend.complete(messages)
        except OllamaUnavailable as e:
            decision = await self._maybe_fallback(decision, e)
            self._log_decision(decision)
            backend = self._backend_for(decision.backend)
            resp = await backend.complete(messages)

        resp.decision = decision
        return resp

    async def stream(
        self,
        messages: list[dict],
        mode: Mode = "auto",
        sensitivity_override: bool | None = None,
    ) -> AsyncIterator[str]:
        """Route and execute a streaming completion.

        Yields string deltas. The :class:`RoutingDecision` is logged at
        INFO before the first chunk.
        """
        decision = self.decide(messages, mode=mode, sensitivity_override=sensitivity_override)
        self._log_decision(decision)

        try:
            backend = self._backend_for(decision.backend)
            async for chunk in backend.stream(messages):
                yield chunk
        except OllamaUnavailable as e:
            decision = await self._maybe_fallback(decision, e)
            self._log_decision(decision)
            backend = self._backend_for(decision.backend)
            async for chunk in backend.stream(messages):
                yield chunk
