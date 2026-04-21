"""Append-only audit log for every guardrail decision.

The :class:`AuditLogger` writes one JSON object per line (JSONL). Records
are never rewritten — this is the forensic trail that proves, months later,
*why* a given action was allowed (or blocked).

A process-wide :class:`threading.Lock` serialises the ``open/write/close``
so concurrent ``evaluate()`` calls from the engine don't interleave lines.
The file is reopened on every call (``"a"`` mode) which is atomically safe
on POSIX under the usual PIPE_BUF line size.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AuditRecord:
    """A single immutable row in the audit log."""

    timestamp: str
    actor: str
    action: str
    environment: str
    risk_score: int
    requested_tier: str
    decision_tier: str
    approvals_received: tuple[str, ...]
    outcome: str
    reasons: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "actor": self.actor,
            "action": self.action,
            "environment": self.environment,
            "risk_score": self.risk_score,
            "requested_tier": self.requested_tier,
            "decision_tier": self.decision_tier,
            "approvals_received": list(self.approvals_received),
            "outcome": self.outcome,
            "reasons": list(self.reasons),
            "metadata": dict(self.metadata),
        }


class AuditLogger:
    """Thread-safe, append-only JSONL audit writer.

    The log file is created lazily on first write; parent directories are
    created as needed. Callers may supply a custom clock for deterministic
    tests.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        clock: "callable[[], datetime] | None" = None,
    ) -> None:
        self._path = Path(path)
        self._clock = clock or _utc_now
        self._lock = threading.Lock()

    @property
    def path(self) -> Path:
        return self._path

    def record(
        self,
        *,
        actor: str,
        action: str,
        environment: str,
        risk_score: int,
        requested_tier: str,
        decision_tier: str,
        approvals_received: tuple[str, ...] | list[str],
        outcome: str,
        reasons: tuple[str, ...] | list[str] = (),
        metadata: dict[str, Any] | None = None,
    ) -> AuditRecord:
        """Build, append, and return an :class:`AuditRecord`."""
        record = AuditRecord(
            timestamp=self._clock().isoformat(),
            actor=actor,
            action=action,
            environment=environment,
            risk_score=int(risk_score),
            requested_tier=str(requested_tier),
            decision_tier=str(decision_tier),
            approvals_received=tuple(approvals_received or ()),
            outcome=str(outcome),
            reasons=tuple(reasons or ()),
            metadata=dict(metadata or {}),
        )
        self._append(record)
        return record

    def iter_records(self) -> list[AuditRecord]:
        """Read records back (for the tests / forensic UI)."""
        if not self._path.exists():
            return []
        out: list[AuditRecord] = []
        with self._path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except ValueError:
                    continue
                out.append(
                    AuditRecord(
                        timestamp=data.get("timestamp", ""),
                        actor=data.get("actor", ""),
                        action=data.get("action", ""),
                        environment=data.get("environment", ""),
                        risk_score=int(data.get("risk_score", 0)),
                        requested_tier=data.get("requested_tier", ""),
                        decision_tier=data.get("decision_tier", ""),
                        approvals_received=tuple(data.get("approvals_received", ())),
                        outcome=data.get("outcome", ""),
                        reasons=tuple(data.get("reasons", ())),
                        metadata=dict(data.get("metadata", {})),
                    )
                )
        return out

    # ------------------------- internals -------------------------

    def _append(self, record: AuditRecord) -> None:
        line = json.dumps(record.to_dict(), sort_keys=True) + "\n"
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            # O_APPEND gives us atomic append-at-EOF semantics on POSIX; we
            # additionally hold an in-process lock so the same Python
            # process's concurrent calls never interleave lines either.
            fd = os.open(
                self._path,
                os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                0o644,
            )
            try:
                os.write(fd, line.encode("utf-8"))
            finally:
                os.close(fd)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
