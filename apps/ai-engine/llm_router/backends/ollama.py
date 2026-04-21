"""Ollama backend for the LLM router.

Thin async wrapper around the Ollama HTTP API
(`https://github.com/ollama/ollama/blob/main/docs/api.md`). Used for
*sensitive* prompts that must not leave the host (Korean PIPA Sep-2026
amendment, customer data, PII, real log payloads).

Endpoints used:

* ``POST /api/chat``       — single-shot or streamed chat completion.
* ``GET  /api/tags``       — health check (list installed models).

The class intentionally avoids the optional ``ollama`` Python package —
we keep the dependency surface small and use ``httpx`` which the rest
of the ai-engine already depends on.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, AsyncIterator

import httpx

if TYPE_CHECKING:  # pragma: no cover
    from ..router import RouterResponse


class OllamaUnavailable(RuntimeError):
    """Raised when the local Ollama daemon cannot be reached.

    This is a *loud* failure by design — the router's default policy
    is to refuse to silently fall back to cloud because doing so could
    cause an unintended cross-border data transfer (PIPA violation).
    """


class OllamaBackend:
    """Backend that routes prompts to a local Ollama daemon."""

    name = "ollama"

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1",
        max_tokens: int = 2048,
        temperature: float = 0.3,
        timeout_s: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout_s = timeout_s

    # ------------------------------------------------------------------ #
    # Health / connectivity
    # ------------------------------------------------------------------ #
    async def health(self) -> bool:
        """Return True if the daemon responds on /api/tags."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except (httpx.HTTPError, OSError):
            return False

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    async def complete(self, messages: list[dict]) -> "RouterResponse":
        """Run a non-streaming completion via ``POST /api/chat``."""
        from ..router import RouterResponse  # local to avoid cycle

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
        except (httpx.ConnectError, httpx.ReadError, OSError) as e:
            raise OllamaUnavailable(
                f"Ollama daemon unreachable at {self.base_url}. "
                "Start it with `ollama serve` or set "
                "fallback_to_cloud_on_local_failure=True in LLMRouterConfig "
                "(not recommended for regulated deployments)."
            ) from e

        if resp.status_code == 404:
            raise OllamaUnavailable(
                f"Ollama model '{self.model}' not installed. "
                f"Pull it with: `ollama pull {self.model}`"
            )
        if resp.status_code >= 400:
            raise OllamaUnavailable(
                f"Ollama returned HTTP {resp.status_code}: {resp.text[:300]}"
            )

        data = resp.json()
        msg = data.get("message", {}) or {}
        text_out = msg.get("content", "") or ""

        usage = {
            "prompt_eval_count": data.get("prompt_eval_count", 0),
            "eval_count": data.get("eval_count", 0),
            "total_duration_ns": data.get("total_duration", 0),
        }

        return RouterResponse(
            text=text_out,
            backend=self.name,
            model=self.model,
            usage=usage,
            finish_reason=data.get("done_reason"),
        )

    async def stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """Stream completion chunks via ``POST /api/chat`` with NDJSON."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload,
                ) as resp:
                    if resp.status_code >= 400:
                        body = await resp.aread()
                        raise OllamaUnavailable(
                            f"Ollama returned HTTP {resp.status_code}: "
                            f"{body.decode('utf-8', errors='replace')[:300]}"
                        )
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        msg = chunk.get("message") or {}
                        piece = msg.get("content", "")
                        if piece:
                            yield piece
                        if chunk.get("done"):
                            break
        except (httpx.ConnectError, httpx.ReadError, OSError) as e:
            raise OllamaUnavailable(
                f"Ollama daemon unreachable at {self.base_url}"
            ) from e
