"""Anthropic Claude backend for the LLM router.

Thin async wrapper around ``anthropic.AsyncAnthropic``. The router
handles sensitivity classification and decision logging; this module
just converts a list of messages into a Claude API call and normalizes
the response.

The import of ``anthropic`` is deferred so the rest of the router
(classifier, Ollama backend, tests) works in environments where
``anthropic`` isn't installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

if TYPE_CHECKING:  # pragma: no cover
    from ..router import RouterResponse


class ClaudeBackend:
    """Backend that routes prompts to the Anthropic API."""

    name = "claude"

    def __init__(
        self,
        model: str = "claude-opus-4-7",
        api_key: str | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.3,
        timeout_s: float = 120.0,
    ):
        self.model = model
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout_s = timeout_s
        self._client = None  # lazy

    # ------------------------------------------------------------------ #
    # Client bootstrap
    # ------------------------------------------------------------------ #
    def _get_client(self):
        """Lazy-import and cache the anthropic async client."""
        if self._client is None:
            try:
                import anthropic  # type: ignore
            except ImportError as e:  # pragma: no cover
                raise RuntimeError(
                    "anthropic package is required for ClaudeBackend. "
                    "Install with `pip install anthropic>=0.42.0`."
                ) from e
            kwargs: dict = {"timeout": self.timeout_s}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            self._client = anthropic.AsyncAnthropic(**kwargs)
        return self._client

    # ------------------------------------------------------------------ #
    # Message normalization
    # ------------------------------------------------------------------ #
    @staticmethod
    def _split_messages(messages: list[dict]) -> tuple[str | None, list[dict]]:
        """Extract a top-level system prompt (if any) from a flat message list.

        The Claude API wants ``system`` as a separate kwarg rather than
        a ``role="system"`` entry, so we peel the first system message off.
        """
        system: str | None = None
        user_and_assistant: list[dict] = []
        for m in messages:
            role = m.get("role")
            content = m.get("content", "")
            if role == "system" and system is None:
                system = content if isinstance(content, str) else str(content)
            else:
                user_and_assistant.append(m)
        return system, user_and_assistant

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    async def complete(self, messages: list[dict]) -> "RouterResponse":
        """Run a one-shot (non-streaming) completion."""
        from ..router import RouterResponse  # local to avoid cycle

        system, chat = self._split_messages(messages)
        client = self._get_client()

        kwargs: dict = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": chat,
        }
        if system:
            kwargs["system"] = system

        resp = await client.messages.create(**kwargs)

        # Flatten content blocks into a single string
        parts: list[str] = []
        for block in getattr(resp, "content", []) or []:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        text_out = "".join(parts)

        usage = getattr(resp, "usage", None)
        usage_dict = {}
        if usage is not None:
            usage_dict = {
                "input_tokens": getattr(usage, "input_tokens", 0),
                "output_tokens": getattr(usage, "output_tokens", 0),
            }

        return RouterResponse(
            text=text_out,
            backend=self.name,
            model=self.model,
            usage=usage_dict,
            finish_reason=getattr(resp, "stop_reason", None),
        )

    async def stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """Stream completion chunks as they arrive.

        Yields plain text deltas. Usage/stop-reason are not surfaced
        per-chunk — callers that need them should use ``complete``.
        """
        system, chat = self._split_messages(messages)
        client = self._get_client()

        kwargs: dict = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": chat,
        }
        if system:
            kwargs["system"] = system

        async with client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                if text:
                    yield text
