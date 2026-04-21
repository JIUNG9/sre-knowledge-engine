# Copyright 2025 June Gu
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
"""Drop-in wrapper around ``anthropic.Anthropic`` that redacts PII.

The proxy preserves the ergonomics of the official SDK — you still call
``client.messages.create(...)`` with the same arguments and receive a
``Message`` object back. Streaming via ``stream=True`` is supported: the
returned stream yields the same events as the underlying SDK, with each
emitted text chunk reverse-substituted so callers never see placeholders.

Design notes:

* The wrapper never mutates the caller's input. It deep-copies the
  ``messages`` and ``system`` arguments before rewriting them.
* Placeholders are scoped to a single ``messages.create`` invocation. A
  new :class:`RequestScope` is allocated at the start and dropped at the
  end unless ``preserve_mapping`` is set (in which case it lingers until
  TTL expiry — useful for multi-turn debugging tools that want to
  un-redact an old response).
* Detection is performed on every string it finds inside user/assistant
  message content (strings and ``{"type": "text", "text": ...}`` blocks)
  and on the ``system`` prompt if present.
* Restoration is performed on every ``TextBlock`` in the response's
  ``content`` list. Non-text blocks (tool use, images) pass through.
"""

from __future__ import annotations

import copy
import logging
from collections.abc import Iterable, Iterator
from typing import Any, TYPE_CHECKING

from proxy.config import PIIProxyConfig
from proxy.detector import PIIDetector
from proxy.mapper import PlaceholderMapper

if TYPE_CHECKING:  # pragma: no cover
    import anthropic

logger = logging.getLogger("aegis.proxy")


class _MessagesProxy:
    """Wraps ``client.messages`` so ``create`` is intercepted."""

    def __init__(self, proxy: AnthropicProxy) -> None:
        self._proxy = proxy

    def create(self, **kwargs: Any) -> Any:
        """Redact arguments, delegate to the real SDK, restore the response."""
        return self._proxy._invoke(kwargs)

    def stream(self, **kwargs: Any) -> Any:  # pragma: no cover - thin alias
        """Alias for ``create(stream=True, ...)`` mirroring the SDK shape."""
        kwargs["stream"] = True
        return self.create(**kwargs)

    def __getattr__(self, item: str) -> Any:
        # Any method we don't explicitly wrap should fall through to the
        # underlying SDK (e.g. ``batches``, ``count_tokens``).
        return getattr(self._proxy._client.messages, item)


class AnthropicProxy:
    """PII-redacting wrapper around an ``anthropic.Anthropic`` client.

    Args:
        client: An instantiated ``anthropic.Anthropic`` (or compatible) client.
        config: Proxy configuration. Defaults to an enabled hybrid proxy.
        detector: Optional pre-built detector. When omitted a fresh one is
            constructed from ``config``.
        mapper: Optional pre-built mapper. When omitted a fresh one is
            constructed from ``config``.

    Attributes:
        messages: A ``_MessagesProxy`` exposing a drop-in ``.create()`` method.

    Example:
        >>> from anthropic import Anthropic
        >>> client = AnthropicProxy(Anthropic())
        >>> resp = client.messages.create(
        ...     model="claude-sonnet-4-6",
        ...     max_tokens=256,
        ...     messages=[{"role": "user", "content": "investigate db01.acme.internal"}],
        ... )
    """

    def __init__(
        self,
        client: "anthropic.Anthropic",
        config: PIIProxyConfig | None = None,
        detector: PIIDetector | None = None,
        mapper: PlaceholderMapper | None = None,
    ) -> None:
        self._client = client
        self._config = config or PIIProxyConfig()
        self._detector = detector or PIIDetector(
            provider=self._config.provider,
            custom_patterns=self._config.custom_patterns,
        )
        self._mapper = mapper or PlaceholderMapper(
            ttl_seconds=self._config.mapping_ttl_seconds
        )
        self.messages = _MessagesProxy(self)

    # ------------------------------------------------------------------ #
    # Fall-through for anything the proxy doesn't explicitly handle.
    # ------------------------------------------------------------------ #
    def __getattr__(self, item: str) -> Any:
        return getattr(self._client, item)

    # ------------------------------------------------------------------ #
    # Invocation pipeline
    # ------------------------------------------------------------------ #
    def _invoke(self, kwargs: dict[str, Any]) -> Any:
        if self._config.is_passthrough():
            return self._client.messages.create(**kwargs)

        scope_id = self._mapper.new_scope()
        streaming = bool(kwargs.get("stream"))
        try:
            redacted_kwargs = self._redact_request(scope_id, kwargs)
            result = self._client.messages.create(**redacted_kwargs)
            if streaming:
                return self._wrap_stream(scope_id, result)
            return self._restore_response(scope_id, result)
        finally:
            # Streaming responses free their scope inside the iterator.
            if not streaming and not self._config.preserve_mapping:
                self._mapper.drop_scope(scope_id)

    # ------------------------------------------------------------------ #
    # Request redaction
    # ------------------------------------------------------------------ #
    def _redact_request(self, scope_id: str, kwargs: dict[str, Any]) -> dict[str, Any]:
        redacted = copy.deepcopy(kwargs)

        system = redacted.get("system")
        if isinstance(system, str):
            redacted["system"] = self._redact_str(scope_id, system)
        elif isinstance(system, list):
            redacted["system"] = [self._redact_content_block(scope_id, b) for b in system]

        messages = redacted.get("messages")
        if isinstance(messages, list):
            for msg in messages:
                if not isinstance(msg, dict):
                    continue
                content = msg.get("content")
                if isinstance(content, str):
                    msg["content"] = self._redact_str(scope_id, content)
                elif isinstance(content, list):
                    msg["content"] = [
                        self._redact_content_block(scope_id, b) for b in content
                    ]
        return redacted

    def _redact_content_block(self, scope_id: str, block: Any) -> Any:
        if isinstance(block, dict):
            if block.get("type") == "text" and isinstance(block.get("text"), str):
                block = dict(block)
                block["text"] = self._redact_str(scope_id, block["text"])
        return block

    def _redact_str(self, scope_id: str, text: str) -> str:
        detections = self._detector.detect(text)
        return self._mapper.redact(scope_id, text, detections)

    # ------------------------------------------------------------------ #
    # Response restoration
    # ------------------------------------------------------------------ #
    def _restore_response(self, scope_id: str, response: Any) -> Any:
        content = getattr(response, "content", None)
        if content is None:
            return response
        for block in content:
            text = getattr(block, "text", None)
            if isinstance(text, str):
                try:
                    block.text = self._mapper.restore(scope_id, text)
                except AttributeError:  # pragma: no cover - frozen models
                    # Pydantic models may be immutable; fall back to setattr.
                    object.__setattr__(block, "text", self._mapper.restore(scope_id, text))
        return response

    def _wrap_stream(self, scope_id: str, stream: Iterable[Any]) -> Iterator[Any]:
        """Yield SDK events with text deltas reverse-substituted.

        We recognize the common event shapes emitted by
        ``anthropic``'s streaming API (``content_block_delta`` with
        ``text_delta``, and raw strings for test doubles). Unknown events
        pass through untouched.
        """
        preserve = self._config.preserve_mapping

        def _iter() -> Iterator[Any]:
            try:
                for event in stream:
                    yield self._restore_stream_event(scope_id, event)
            finally:
                if not preserve:
                    self._mapper.drop_scope(scope_id)

        return _iter()

    def _restore_stream_event(self, scope_id: str, event: Any) -> Any:
        # anthropic SDK style: event.delta.text
        delta = getattr(event, "delta", None)
        if delta is not None:
            text = getattr(delta, "text", None)
            if isinstance(text, str):
                try:
                    delta.text = self._mapper.restore(scope_id, text)
                except AttributeError:  # pragma: no cover
                    object.__setattr__(delta, "text", self._mapper.restore(scope_id, text))
            partial = getattr(delta, "partial_json", None)
            if isinstance(partial, str):
                try:
                    delta.partial_json = self._mapper.restore(scope_id, partial)
                except AttributeError:  # pragma: no cover
                    object.__setattr__(
                        delta, "partial_json", self._mapper.restore(scope_id, partial)
                    )
        # Dict-style events (mock transports / test doubles).
        if isinstance(event, dict):
            event = dict(event)
            if isinstance(event.get("delta"), dict):
                d = dict(event["delta"])
                if isinstance(d.get("text"), str):
                    d["text"] = self._mapper.restore(scope_id, d["text"])
                event["delta"] = d
            if isinstance(event.get("text"), str):
                event["text"] = self._mapper.restore(scope_id, event["text"])
        # Plain strings from test doubles.
        if isinstance(event, str):
            return self._mapper.restore(scope_id, event)
        return event

    # ------------------------------------------------------------------ #
    # Introspection
    # ------------------------------------------------------------------ #
    @property
    def config(self) -> PIIProxyConfig:
        """Return the active configuration (read-only view)."""
        return self._config

    @property
    def mapper(self) -> PlaceholderMapper:
        """Expose the underlying mapper, mostly for testing and debugging."""
        return self._mapper
