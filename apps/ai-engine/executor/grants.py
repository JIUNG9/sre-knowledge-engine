"""Execution grants — server-side proof that an action was approved.

A grant is minted in-process, after a decision has cleared the tier and
approval gates, and handed to whoever will trigger the run. It carries
nothing the caller can edit: the executor looks the grant up by id and
rebuilds the decision from what it stored.

Three properties hold for every grant:

* **Bound** — the grant stores a SHA-256 digest of the exact action it
  approved (verb, target, environment, category, metadata, ...). Any
  change to the action, including ``metadata.replicas``, is a mismatch.
* **Short-lived** — default TTL is 15 minutes
  (``AEGIS_EXECUTOR_GRANT_TTL_SECONDS``).
* **Single use** — :meth:`GrantStore.consume` removes the grant under a
  lock, so two concurrent requests can't both run it.

The default store is in memory. That is correct for one process. Several
replicas, or several uvicorn workers, need a shared store implementing
the same three methods (``issue`` / ``peek`` / ``consume``); without one
a grant only works in the process that issued it (fails closed).
"""

from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

DEFAULT_GRANT_TTL_SECONDS = 900
MAX_GRANT_TTL_SECONDS = 3600

# Every ProposedAction field that can change what a wrapper runs, or how
# the executor routes it. Name and blast radius are included too: an
# approver saw them, so they're part of what was approved.
_DIGEST_FIELDS = (
    "name",
    "verb",
    "target",
    "environment",
    "category",
    "blast_radius",
    "reversible",
    "metadata",
)


def action_digest(action: Any) -> str:
    """Return a stable SHA-256 hex digest of ``action``.

    Works on any object with the ProposedAction attribute shape. Keys are
    sorted and separators fixed so the same action always hashes the
    same way. Values must be plain JSON types: an Enum or custom object
    raises ``TypeError`` instead of being stringified, so two different
    values can't hash the same through ``str()``.
    """
    body = {f: getattr(action, f, None) for f in _DIGEST_FIELDS}
    body["metadata"] = dict(body["metadata"] or {})
    canonical = json.dumps(
        body, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class GrantError(Exception):
    """Raised when a grant can't be used. ``reason`` is audit-safe."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Grant:
    """One approved action, as the server recorded it."""

    grant_id: str
    digest: str
    tier: str
    approvers: tuple[str, ...]
    required_approvals: int
    backend: str
    issued_at: float
    expires_at: float


class GrantStore:
    """Thread-safe in-memory grant store."""

    def __init__(
        self,
        *,
        ttl_seconds: int = DEFAULT_GRANT_TTL_SECONDS,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if not 0 < ttl_seconds <= MAX_GRANT_TTL_SECONDS:
            raise ValueError(
                f"grant TTL must be between 1 and {MAX_GRANT_TTL_SECONDS} seconds"
            )
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._grants: dict[str, Grant] = {}

    def issue(
        self,
        action: Any,
        *,
        tier: str,
        approvers: tuple[str, ...],
        required_approvals: int,
        backend: str,
    ) -> Grant:
        now = self._clock()
        grant = Grant(
            grant_id=secrets.token_urlsafe(24),
            digest=action_digest(action),
            tier=tier,
            approvers=tuple(approvers),
            required_approvals=required_approvals,
            backend=backend,
            issued_at=now,
            expires_at=now + self.ttl_seconds,
        )
        with self._lock:
            self._sweep(now)
            self._grants[grant.grant_id] = grant
        return grant

    def peek(self, grant_id: str, action: Any) -> Grant:
        """Validate without using the grant up (for dry-run previews)."""
        with self._lock:
            return self._check(grant_id, action, consume=False)

    def consume(self, grant_id: str, action: Any) -> Grant:
        """Validate and remove the grant in one step."""
        with self._lock:
            return self._check(grant_id, action, consume=True)

    def __len__(self) -> int:
        with self._lock:
            return len(self._grants)

    # Caller holds the lock.
    def _check(self, grant_id: str, action: Any, *, consume: bool) -> Grant:
        now = self._clock()
        grant = self._grants.get(grant_id or "")
        if grant is None:
            raise GrantError("grant_unknown_or_used")
        if now >= grant.expires_at:
            del self._grants[grant_id]
            raise GrantError("grant_expired")
        # A mismatch doesn't burn the grant: the approved action can still
        # run, and grant ids are 192-bit random so they can't be guessed.
        if not secrets.compare_digest(grant.digest, action_digest(action)):
            raise GrantError("grant_action_mismatch")
        if consume:
            del self._grants[grant_id]
        return grant

    def _sweep(self, now: float) -> None:
        expired = [gid for gid, g in self._grants.items() if now >= g.expires_at]
        for gid in expired:
            del self._grants[gid]
