"""In-memory job run history.

The scheduler API surfaces recent run outcomes via
``GET /api/v1/scheduler/history``. We deliberately keep history in
process memory rather than reaching for Redis or Postgres — the
scheduler is a single-process supervisor and history is best-effort
debugging info, not durable audit data. (For durable audit, the
kill-switch / synthesizer layers already write JSONL to disk.)
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Deque, Literal

JobOutcome = Literal["success", "skipped", "failed"]


@dataclass
class JobRunRecord:
    """One row of history: a single scheduled execution's outcome.

    Attributes:
        job_id: The :class:`Job` id this record belongs to.
        started_at: ISO-8601 UTC timestamp at run entry.
        finished_at: ISO-8601 UTC timestamp at run exit (None if mid-flight).
        duration_ms: Wall time in milliseconds; None if mid-flight.
        outcome: One of ``"success"``, ``"skipped"``, ``"failed"``.
        error: Exception repr if outcome=="failed", else None.
        detail: Free-form metadata (counts, lookback windows, etc.).
    """

    job_id: str
    started_at: str
    finished_at: str | None = None
    duration_ms: float | None = None
    outcome: JobOutcome = "success"
    error: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "outcome": self.outcome,
            "error": self.error,
            "detail": dict(self.detail),
        }


class JobHistory:
    """Bounded in-memory ring buffer of :class:`JobRunRecord` per job id.

    Thread-safe (``threading.Lock``) so APScheduler workers and the
    FastAPI request handler can share it without coordination.
    """

    def __init__(self, max_per_job: int = 100) -> None:
        self._max_per_job = max(1, max_per_job)
        self._records: dict[str, Deque[JobRunRecord]] = {}
        self._lock = Lock()

    def record(self, run: JobRunRecord) -> None:
        """Append ``run`` for its job, evicting oldest if the cap is reached."""
        with self._lock:
            bucket = self._records.setdefault(
                run.job_id, deque(maxlen=self._max_per_job)
            )
            bucket.append(run)

    def list(
        self,
        *,
        job_id: str | None = None,
        limit: int = 50,
    ) -> list[JobRunRecord]:
        """Return the most-recent ``limit`` runs, optionally filtered by id.

        Returns newest-first to match the typical UX.
        """
        limit = max(1, limit)
        with self._lock:
            if job_id:
                bucket = self._records.get(job_id, deque())
                return list(reversed(list(bucket)))[:limit]
            merged: list[JobRunRecord] = []
            for bucket in self._records.values():
                merged.extend(bucket)
        merged.sort(key=lambda r: r.started_at, reverse=True)
        return merged[:limit]

    def last_run(self, job_id: str) -> JobRunRecord | None:
        """Return the most-recent run for ``job_id``, or None if none yet."""
        with self._lock:
            bucket = self._records.get(job_id)
            if not bucket:
                return None
            return bucket[-1]


def utc_now_iso() -> str:
    """Helper for consistent ISO-8601 UTC timestamps across the package."""
    return datetime.now(timezone.utc).isoformat()
