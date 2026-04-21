# Copyright 2025 June Gu
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
"""Reversible placeholder mapper with TTL and request scoping.

Every outbound Claude call gets its own :class:`RequestScope`. Inside a
scope, the same raw value is always replaced with the same placeholder (so
repeated mentions of ``db01.acme.internal`` collapse to a single
``<HOST_1>``). Scopes do **not** share placeholders — a value that was
``<HOST_1>`` in one request will be ``<HOST_1>`` again in a different
request only by coincidence. This prevents cross-request leakage if a
mapping for request A were ever applied to response B.

The store is fully thread-safe via a single ``threading.RLock`` guarding
the dict. Expired scopes are evicted lazily on read and eagerly when
:meth:`PlaceholderMapper.sweep` is called.
"""

from __future__ import annotations

import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from proxy.detector import Detection

# Regex used to locate placeholders during reverse substitution.
_PLACEHOLDER_RE = re.compile(r"<([A-Z][A-Z0-9_]*)_(\d+)>")


@dataclass
class RequestScope:
    """Per-request redaction state.

    Attributes:
        scope_id: Opaque identifier, usually a UUID4 hex string.
        created_at: Unix timestamp, used for TTL eviction.
        forward: value -> placeholder, used to collapse duplicate mentions.
        reverse: placeholder -> value, used during response rewriting.
        counters: category -> next integer suffix to hand out.
    """

    scope_id: str
    created_at: float
    forward: dict[str, str] = field(default_factory=dict)
    reverse: dict[str, str] = field(default_factory=dict)
    counters: dict[str, int] = field(default_factory=dict)

    def placeholder_for(self, category: str, value: str) -> str:
        """Return (creating if necessary) the placeholder for ``value``."""
        existing = self.forward.get(value)
        if existing is not None:
            return existing
        n = self.counters.get(category, 0) + 1
        self.counters[category] = n
        placeholder = f"<{category}_{n}>"
        self.forward[value] = placeholder
        self.reverse[placeholder] = value
        return placeholder


class PlaceholderMapper:
    """Thread-safe registry of per-request redaction scopes.

    The mapper's public methods are the only safe way to create scopes,
    redact strings, and restore responses. All state lives on the instance,
    never in module globals — this means tests can freely instantiate
    independent mappers without bleed-through.

    Args:
        ttl_seconds: Scopes older than this are evicted. Defaults to ``3600``.
    """

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._ttl = ttl_seconds
        self._scopes: dict[str, RequestScope] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------ #
    # Scope lifecycle
    # ------------------------------------------------------------------ #
    def new_scope(self) -> str:
        """Allocate a fresh scope and return its id."""
        scope_id = uuid.uuid4().hex
        with self._lock:
            self._scopes[scope_id] = RequestScope(
                scope_id=scope_id,
                created_at=time.time(),
            )
        return scope_id

    def drop_scope(self, scope_id: str) -> None:
        """Delete a scope immediately. Idempotent."""
        with self._lock:
            self._scopes.pop(scope_id, None)

    def sweep(self) -> int:
        """Evict all expired scopes. Returns the count removed."""
        cutoff = time.time() - self._ttl
        with self._lock:
            expired = [sid for sid, s in self._scopes.items() if s.created_at < cutoff]
            for sid in expired:
                del self._scopes[sid]
        return len(expired)

    # ------------------------------------------------------------------ #
    # Redact / restore
    # ------------------------------------------------------------------ #
    def redact(self, scope_id: str, text: str, detections: list[Detection]) -> str:
        """Rewrite ``text`` replacing each detection with its placeholder.

        Detections must be non-overlapping and sorted ascending by ``start``
        (the contract produced by :class:`~proxy.detector.PIIDetector`).
        """
        if not detections:
            return text
        scope = self._get(scope_id)
        if scope is None:
            raise KeyError(f"unknown or expired scope: {scope_id}")

        out_parts: list[str] = []
        cursor = 0
        with self._lock:
            for d in detections:
                if d.start < cursor:
                    # Defensive: overlapping ranges should have been merged.
                    continue
                out_parts.append(text[cursor : d.start])
                out_parts.append(scope.placeholder_for(d.category, d.value))
                cursor = d.end
            out_parts.append(text[cursor:])
        return "".join(out_parts)

    def restore(self, scope_id: str, text: str) -> str:
        """Reverse-substitute any placeholders known to ``scope_id``.

        Unknown placeholders are left untouched (they may belong to a
        different scope or be literal text).
        """
        scope = self._get(scope_id)
        if scope is None or not text:
            return text

        def _sub(match: re.Match[str]) -> str:
            placeholder = match.group(0)
            return scope.reverse.get(placeholder, placeholder)

        return _PLACEHOLDER_RE.sub(_sub, text)

    # ------------------------------------------------------------------ #
    # Introspection (tests / debugging)
    # ------------------------------------------------------------------ #
    def mapping(self, scope_id: str) -> dict[str, str]:
        """Return a copy of the placeholder->value map for ``scope_id``."""
        scope = self._get(scope_id)
        if scope is None:
            return {}
        with self._lock:
            return dict(scope.reverse)

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _get(self, scope_id: str) -> RequestScope | None:
        with self._lock:
            scope = self._scopes.get(scope_id)
            if scope is None:
                return None
            if scope.created_at < time.time() - self._ttl:
                del self._scopes[scope_id]
                return None
            return scope
