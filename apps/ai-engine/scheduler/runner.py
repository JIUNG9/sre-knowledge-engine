"""Safety wrapper around every scheduled execution.

For each job tick the runner:
  1. Checks the kill switch. If active, the run is recorded as
     ``skipped`` and the OTel span is tagged accordingly. The work
     function is NEVER called.
  2. Opens an OTel span ``aegis.scheduler.job`` carrying
     ``aegis.job.name``, ``aegis.job.interval_minutes``, and
     (after the run) ``aegis.job.outcome``.
  3. Catches every exception. A failed job logs structured details and
     records a ``failed`` history row, but does NOT propagate — the
     scheduler must keep ticking.
  4. Records wall-time duration in milliseconds on the span and history.

The wrapper is exposed as both a callable factory
(:meth:`JobRunner.wrap`) and a thin module-level helper
(:func:`run_with_safety`) so callers that already hold a runner can
share its history, while ad-hoc callers can dispatch a one-off run
without constructing one.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from .history import JobHistory, JobRunRecord

if TYPE_CHECKING:
    from .jobs import Job

logger = logging.getLogger("aegis.scheduler.runner")

# A no-op kill switch protocol: anything with a sync ``is_active() -> bool``
# satisfies the runner. Tests pass a tiny stub; production wires
# :class:`killswitch.KillSwitch`.
KillSwitchLike = Callable[..., Any]


class JobRunner:
    """Wraps :class:`Job` execution with kill-switch + OTel + history.

    Args:
        history: Where to record run outcomes.
        killswitch: Object exposing ``is_active() -> bool``. ``None`` =
            kill switch disabled (every run proceeds).
        on_run: Optional async hook invoked after every recorded run.
            Used by the scheduler tests to deterministically wait for a
            tick to land in history without polling.
    """

    def __init__(
        self,
        history: JobHistory,
        *,
        killswitch: Any | None = None,
        on_run: Callable[[JobRunRecord], Awaitable[None]] | None = None,
    ) -> None:
        self.history = history
        self.killswitch = killswitch
        self._on_run = on_run

    def wrap(self, job: "Job") -> Callable[[], Awaitable[JobRunRecord]]:
        """Return an async callable APScheduler can register.

        The returned coroutine is what APScheduler invokes every tick.
        It always resolves to a :class:`JobRunRecord` and never raises.
        """

        async def _run() -> JobRunRecord:
            return await self._execute(job)

        _run.__name__ = f"scheduled_{job.id}"
        return _run

    async def run_once(self, job: "Job") -> JobRunRecord:
        """Run ``job`` immediately, bypassing APScheduler.

        Used by the ``POST /api/v1/scheduler/jobs/{id}/run`` endpoint
        so an operator can trigger a sync without waiting for the next
        tick. Kill-switch + OTel still apply.
        """
        return await self._execute(job)

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    async def _execute(self, job: "Job") -> JobRunRecord:
        """Core safety pipeline: span open -> killswitch -> func -> record."""
        started = time.monotonic()
        started_at = datetime.now(timezone.utc).isoformat()

        # --- Kill switch check (before opening any span work) ---
        if self._killswitch_active():
            logger.warning(
                "scheduler: kill switch active; skipping job %s", job.id
            )
            record = JobRunRecord(
                job_id=job.id,
                started_at=started_at,
                finished_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=(time.monotonic() - started) * 1000.0,
                outcome="skipped",
                error=None,
                detail={"reason": "killswitch_active", **job.metadata},
            )
            self._emit_span(job, record)
            self.history.record(record)
            await self._fire_on_run(record)
            return record

        # --- Run with exception isolation ---
        outcome: str = "success"
        err_text: str | None = None
        detail: dict[str, Any] = dict(job.metadata)

        try:
            result = await job.func()
            if isinstance(result, dict):
                # Merge but don't let user data clobber connector metadata.
                for key, value in result.items():
                    detail.setdefault(key, value)
        except Exception as exc:  # noqa: BLE001 — must NEVER kill scheduler
            outcome = "failed"
            err_text = repr(exc)
            logger.exception("scheduler: job %s failed", job.id)

        finished = datetime.now(timezone.utc).isoformat()
        duration_ms = (time.monotonic() - started) * 1000.0

        record = JobRunRecord(
            job_id=job.id,
            started_at=started_at,
            finished_at=finished,
            duration_ms=duration_ms,
            outcome=outcome,  # type: ignore[arg-type]
            error=err_text,
            detail=detail,
        )
        self._emit_span(job, record)
        self.history.record(record)

        if outcome == "success":
            logger.info(
                "scheduler: job %s ok in %.1fms", job.id, duration_ms
            )
        await self._fire_on_run(record)
        return record

    def _killswitch_active(self) -> bool:
        """Best-effort kill-switch read.

        We deliberately swallow read errors. The kill switch is meant to
        gate destructive actions; if its backend is unreachable we'd
        rather let the sync proceed than freeze the supervisor on a
        monitoring outage. (The killswitch module itself logs.)
        """
        if self.killswitch is None:
            return False
        try:
            return bool(self.killswitch.is_active())
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "scheduler: killswitch.is_active() raised %r — proceeding", exc
            )
            return False

    def _emit_span(self, job: "Job", record: JobRunRecord) -> None:
        """Best-effort OTel span emission.

        OTel is an optional dep at runtime — if the import or tracer
        construction fails we still want the run to be recorded in
        history, so failures here are swallowed.
        """
        try:
            from opentelemetry import trace
            from opentelemetry.trace import Status, StatusCode
        except Exception:  # pragma: no cover - OTel not installed
            return

        try:
            tracer = trace.get_tracer("aegis.scheduler", "0.4.0")
            with tracer.start_as_current_span("aegis.scheduler.job") as span:
                span.set_attribute("aegis.job.id", job.id)
                span.set_attribute("aegis.job.name", job.name)
                span.set_attribute(
                    "aegis.job.interval_minutes", float(job.interval_minutes)
                )
                span.set_attribute("aegis.job.outcome", record.outcome)
                if record.duration_ms is not None:
                    span.set_attribute(
                        "aegis.job.duration_ms", float(record.duration_ms)
                    )
                if record.error:
                    span.set_attribute("aegis.job.error", record.error)
                # Surface lookback / topics / connector for debugging.
                for key, value in job.metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        span.set_attribute(f"aegis.job.meta.{key}", value)
                    else:
                        span.set_attribute(
                            f"aegis.job.meta.{key}", repr(value)
                        )
                if record.outcome == "failed":
                    span.set_status(
                        Status(StatusCode.ERROR, record.error or "failed")
                    )
                else:
                    span.set_status(Status(StatusCode.OK))
        except Exception as exc:  # pragma: no cover
            logger.debug("scheduler: OTel span emit failed: %s", exc)

    async def _fire_on_run(self, record: JobRunRecord) -> None:
        if self._on_run is None:
            return
        try:
            await self._on_run(record)
        except Exception:  # pragma: no cover - hook errors mustn't escape
            logger.exception("scheduler: on_run hook raised")


async def run_with_safety(
    job: "Job",
    *,
    history: JobHistory,
    killswitch: Any | None = None,
) -> JobRunRecord:
    """Module-level shortcut for one-off safe execution.

    Equivalent to constructing a :class:`JobRunner` and calling
    :meth:`run_once`. Useful for ad-hoc CLI / test invocation that does
    not own a :class:`Scheduler`.
    """
    runner = JobRunner(history, killswitch=killswitch)
    return await runner.run_once(job)
