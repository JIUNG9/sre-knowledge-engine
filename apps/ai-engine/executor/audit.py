"""Append-only JSONL audit log for the executor (Layer 4 / Phase 2.5).

Every executor invocation produces ONE line in the audit log — even
refusals. The line contains enough metadata to forensically reconstruct
"who tried to run what, what gate said no, what the LLM saw" without
storing raw stdout/stderr (which often contains PII or secret material).

Instead, the audit row stores SHA-256 hashes of stdout/stderr. The
operator may separately persist the raw streams under their own
retention policy and cross-reference by the hash.

The writer is process-thread-safe via a small in-memory lock. Because
each ``record()`` opens, writes one line, then closes the file, multiple
processes (e.g. uvicorn workers) can append safely on POSIX as long as
each line is below ``PIPE_BUF`` — which our records always are.
"""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(value: str) -> str:
    """Stable SHA-256 hex of ``value`` (utf-8). Empty string -> sha256("")."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ExecutorAuditRecord:
    """One immutable row in the executor audit log."""

    audit_id: str
    timestamp: str
    investigation_id: str | None
    action: str
    verb: str
    target: str
    environment: str
    tier: str
    approvals: tuple[str, ...]
    outcome: str
    exit_code: int | None
    stdout_hash: str
    stderr_hash: str
    duration_ms: float
    dry_run: bool
    refused_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["approvals"] = list(self.approvals)
        return d


class AuditLogger:
    """Append-only JSONL writer for executor decisions.

    Records are written one JSON object per line. The writer never reads
    the file back — that is a deliberate design choice. Reading is the
    job of the ``GET /api/v1/executor/audit`` endpoint, which uses a
    separate ``read_recent`` helper. This keeps the hot path (every
    executor call) write-only.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        # Process-local de-dupe for idempotency. Maps (investigation_id,
        # action_hash) -> audit_id. Only consulted within a single
        # process/runtime; the on-disk log is the durable truth.
        self._seen: dict[tuple[str, str], str] = {}

    @property
    def path(self) -> Path:
        return self._path

    def _idempotency_key(
        self, investigation_id: str | None, action: str, verb: str, target: str
    ) -> tuple[str, str] | None:
        if not investigation_id:
            return None
        digest = _sha256(f"{action}|{verb}|{target}")
        return (investigation_id, digest)

    def record(
        self,
        *,
        investigation_id: str | None,
        action: str,
        verb: str,
        target: str,
        environment: str,
        tier: str,
        approvals: tuple[str, ...] | list[str],
        outcome: str,
        exit_code: int | None,
        stdout: str,
        stderr: str,
        duration_ms: float,
        dry_run: bool,
        refused_reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutorAuditRecord:
        """Persist one record. Idempotent per (investigation_id, action).

        If a record with the same key was already written *in this
        process* the prior :class:`ExecutorAuditRecord` is returned
        unchanged. The on-disk log is the durable source of truth; the
        in-process cache is a defensive shield against accidental retries
        within the same investigation.
        """
        key = self._idempotency_key(investigation_id, action, verb, target)
        if key is not None and key in self._seen:
            audit_id = self._seen[key]
            # Reconstruct a stub record — the caller only needs audit_id.
            return ExecutorAuditRecord(
                audit_id=audit_id,
                timestamp=_utc_now(),
                investigation_id=investigation_id,
                action=action,
                verb=verb,
                target=target,
                environment=environment,
                tier=tier,
                approvals=tuple(approvals or ()),
                outcome="duplicate",
                exit_code=exit_code,
                stdout_hash=_sha256(stdout),
                stderr_hash=_sha256(stderr),
                duration_ms=duration_ms,
                dry_run=dry_run,
                refused_reason="duplicate_invocation",
                metadata=dict(metadata or {}),
            )

        record = ExecutorAuditRecord(
            audit_id=uuid.uuid4().hex,
            timestamp=_utc_now(),
            investigation_id=investigation_id,
            action=action,
            verb=verb,
            target=target,
            environment=environment,
            tier=tier,
            approvals=tuple(approvals or ()),
            outcome=outcome,
            exit_code=exit_code,
            stdout_hash=_sha256(stdout),
            stderr_hash=_sha256(stderr),
            duration_ms=duration_ms,
            dry_run=dry_run,
            refused_reason=refused_reason,
            metadata=dict(metadata or {}),
        )
        self._write_line(record.to_dict())
        if key is not None:
            self._seen[key] = record.audit_id
        return record

    def _write_line(self, payload: dict[str, Any]) -> None:
        path = self._path
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(payload, sort_keys=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
                fh.flush()

    def read_recent(
        self,
        *,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Read up to ``limit`` recent rows (newest first).

        Optional ``since`` filter compares against record ``timestamp``.
        Missing file -> empty list. Malformed lines are skipped silently
        (forensics tooling will pick them up out-of-band).
        """
        if not self._path.exists():
            return []
        with self._path.open("r", encoding="utf-8") as fh:
            raw_lines = fh.readlines()
        rows: list[dict[str, Any]] = []
        for raw in raw_lines:
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if since is not None:
                ts = obj.get("timestamp")
                if not isinstance(ts, str):
                    continue
                try:
                    parsed = datetime.fromisoformat(ts)
                except ValueError:
                    continue
                if parsed < since:
                    continue
            rows.append(obj)
        rows.reverse()  # newest first
        return rows[: max(0, int(limit))]

    def flush(self) -> None:
        """Best-effort flush. Currently a no-op (we open+close per write)."""
        return None
